from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
import sqlalchemy as sa
from sqlalchemy import cast, Integer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.db import models as m
from app.clients.anisongdb import (
    fetch_by_mal_ids,
    search_by_title,
    parse_use_type_and_seq,
    explode_names_from_string,
    fetch_songs_by_artist_ids,
    fetch_songs_by_composer_ids,
    search_songs_for_person
)


def _first(*vals):
    for v in vals:
        if v:
            return v
    return None


def _to_int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
    

def _parse_season_year(vintage: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """
    AniSongDB 'animeVintage' examples: 'Spring 2014', 'Summer 2021', etc.
    Returns (season, year) or (None, None).
    """
    if not vintage:
        return None, None
    parts = str(vintage).split()
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0], int(parts[1])
    return None, None


def _extract_linked_ids(row: Dict[str, Any]) -> Dict[str, int]:
    """
    Extract a clean dict of linked ids (ints) from a SongEntry.
    Expected keys inside row.get('linked_ids'): 'anilist', 'myanimelist'.
    Safely drops non-integer values.
    """
    linked = (row.get("linked_ids") or {}) if isinstance(row.get("linked_ids"), dict) else {}
    out: Dict[str, int] = {}
    for k in ("anilist", "myanimelist"):
        iv = _to_int(linked.get(k))
        if iv is not None:
            out[k] = iv
    return out


def _find_anime_by_linked_ids(db: Session, linked: Dict[str, int]) -> Optional[m.Anime]:
    """
    Prefer AniList match, then MAL match. Uses JSONB lookups on Anime.linked_ids.
    """
    if not linked:
        return None

    ani = linked.get("anilist")
    if ani is not None:
        row = (
            db.query(m.Anime)
              .filter(cast(m.Anime.linked_ids["anilist"].astext, Integer) == int(ani))
              .first()
        )
        if row:
            return row

    mal = linked.get("myanimelist")
    if mal is not None:
        row = (
            db.query(m.Anime)
              .filter(cast(m.Anime.linked_ids["myanimelist"].astext, Integer) == int(mal))
              .first()
        )
        if row:
            return row

    return None


def _get_or_create_anime_from_row(db: Session, row: Dict[str, Any]) -> m.Anime:
    """
    Given a SongEntry row from AniSongDB, find or create the Anime it belongs to.
    - Lookup by linked_ids (AniList, then MAL)
    - Else create with english/japanese titles and (season, year) parsed from 'animeVintage'
    - Do not commit; caller controls the transaction
    """
    linked = _extract_linked_ids(row)
    found = _find_anime_by_linked_ids(db, linked)
    if found:
        return found

    season, year = _parse_season_year(row.get("animeVintage"))

    en = row.get("animeENName")
    jp = row.get("animeJPName")
    romaji = row.get("animeRomajiName") or en or jp  # if your payload has romaji

    new_row = m.Anime(
        title_en=en,
        title_jp=jp,
        title_romaji=romaji,
        season=season,
        year=year,
        type=None,                # you can infer from another field if present
        cover_image_url=None,     # fill later if available
        linked_ids=linked,
    )
    db.add(new_row)
    db.flush()  # assign PK without committing
    return new_row
    

def _names_from_artist_obj(a: Dict[str, Any]) -> list[str]:
    names = a.get("names") or []
    return [n for n in names if isinstance(n, str) and n.strip()]


def _primary_name_from_artist_obj(a: Dict[str, Any]) -> Optional[str]:
    names = _names_from_artist_obj(a)
    return names[0] if names else None


def _get_or_create_person(
    db: Session,
    name: str,
    anisongdb_id: Optional[int] = None,
    *,
    kind: str = "person",
) -> m.People:
    """
    Prefer lookup by anisongdb_id (unique), else by primary_name.
    If found-by-name and missing id, backfill anisongdb_id.
    If kind differs (e.g., we learn it's a group), update to the stronger info.
    """
    # by id
    if anisongdb_id is not None:
        row = db.query(m.People).filter(m.People.anisongdb_id == anisongdb_id).first()
        if row:
            # update kind if we learn it's a group
            if kind == "group" and row.kind != "group":
                row.kind = "group"
            # add alt-name if useful
            if name and row.primary_name != name and name not in (row.alt_names or []):
                row.alt_names = [*(row.alt_names or []), name]
            return row

    # by name
    row = db.query(m.People).filter(m.People.primary_name == name).first()
    if row:
        if anisongdb_id is not None and row.anisongdb_id is None:
            row.anisongdb_id = anisongdb_id
        if kind == "group" and row.kind != "group":
            row.kind = "group"
        return row

    # create
    row = m.People(
        kind=kind,
        primary_name=name,
        alt_names=[],
        image_url=None,
        external_links={},
        anisongdb_id=anisongdb_id,
    )
    db.add(row)
    db.flush()
    return row


def _get_or_create_song(db: Session, name: str, *, audio: str) -> m.Song:
    row = db.query(m.Song).filter(m.Song.name == name).first()
    if row:
        if audio and not row.audio:
            row.audio = audio
        return row
    row = m.Song(name=name, audio=audio or "")
    db.add(row)
    db.flush()
    return row


def _ensure_credit(db: Session, song_id, people_name: str, role: str, anisongdb_id: Optional[int] = None) -> None:
    p = _get_or_create_person(db, people_name, anisongdb_id=anisongdb_id)
    stmt = pg_insert(m.SongArtist.__table__).values(song_id=song_id, people_id=p.id, role=role)
    stmt = stmt.on_conflict_do_nothing(index_elements=["song_id", "people_id", "role"])
    db.execute(stmt)
    

def _ensure_credit_by_id(db: Session, song_id, people_id, role: str) -> None:
    stmt = pg_insert(m.SongArtist.__table__).values(
        song_id=song_id, people_id=people_id, role=role
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["song_id", "people_id", "role"])
    db.execute(stmt)
    

def _ensure_membership(db: Session, group: m.People, member: m.People) -> None:
    """
    Insert a PeopleMembership (group -> member) if not present.
    """
    stmt = pg_insert(m.PeopleMembership.__table__).values(
        group_id=group.id, member_id=member.id
    )
    # PK is (group_id, member_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=["group_id", "member_id"])
    db.execute(stmt)
    

def _merge_alt_names(existing: list[str] | None, incoming: list[str]) -> list[str]:
    out: list[str] = list(existing or [])
    for n in incoming:
        n = (n or "").strip()
        if n and n not in out:
            out.append(n)
    return out


def _upsert_artist_entity(db: Session, a: Dict[str, Any]) -> m.People:
    """
    Build/merge a People row from an AniSongDB 'Artist' object, including group membership.
    - Decides kind by presence of 'members' (group) vs not (person).
    - Merges alt_names from the names list.
    - For groups: ensures PeopleMemberships to members.
    - For persons: ensures PeopleMemberships to groups they belong to.
    Returns the People row for this artist (group or person).
    """
    aid = _to_int(a.get("id"))
    names = _names_from_artist_obj(a)
    primary = names[0] if names else None
    if not primary:
        # fall back to a safe placeholder to avoid empty names
        primary = f"Artist {aid}" if aid is not None else "Unknown Artist"

    is_group = bool(a.get("members"))
    kind = "group" if is_group else "person"

    # upsert the main entity
    person = _get_or_create_person(db, primary, anisongdb_id=aid, kind=kind)
    # merge alt-names (do not duplicate primary)
    alts = [n for n in names if n != person.primary_name]
    person.alt_names = _merge_alt_names(person.alt_names, alts)

    # If it's a group, upsert members and link them
    if is_group:
        for mem in (a.get("members") or []):
            mem_id = _to_int((mem or {}).get("id"))
            mem_name = _primary_name_from_artist_obj(mem) or (f"Artist {mem_id}" if mem_id is not None else None)
            if not mem_name:
                continue
            member = _get_or_create_person(db, mem_name, anisongdb_id=mem_id, kind="person")
            # merge member alt-names too
            member.alt_names = _merge_alt_names(member.alt_names, _names_from_artist_obj(mem)[1:])
            _ensure_membership(db, group=person, member=member)

    # If it's a person and they list groups, link them to those groups
    for grp in (a.get("groups") or []):
        gid = _to_int((grp or {}).get("id"))
        gname = _primary_name_from_artist_obj(grp) or (f"Group {gid}" if gid is not None else None)
        if not gname:
            continue
        group = _get_or_create_person(db, gname, anisongdb_id=gid, kind="group")
        group.alt_names = _merge_alt_names(group.alt_names, _names_from_artist_obj(grp)[1:])
        _ensure_membership(db, group=group, member=person)

    return person


def _link_once(
    db: Session,
    song: m.Song,
    anime: m.Anime,
    *,
    use_type: str,
    sequence: Optional[int],
    notes: Optional[str],
    is_dub: Optional[bool],
    is_rebroadcast: Optional[bool],
) -> None:
    """
    Insert or update a SongAnime link exactly once.

    - On first insert: writes use_type, sequence, notes, is_dub, is_rebroadcast
    - On conflict (same song/anime/use_type/sequence): keeps the first non-null notes,
      and ORs the booleans so flags can only flip False->True (never True->False)
    """
    vals = {
        "song_id": song.id,
        "anime_id": anime.id,
        "use_type": use_type,
        "sequence": sequence,
        "notes": notes,
        "is_dub": bool(is_dub or False),
        "is_rebroadcast": bool(is_rebroadcast or False),
    }

    stmt = pg_insert(m.SongAnime.__table__).values(vals)

    # Use your unique constraint name for the link (adjust if yours differs)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_song_anime_usage",
        set_={
            # accumulate truth
            "is_dub": sa.text("song_anime.is_dub OR EXCLUDED.is_dub"),
            "is_rebroadcast": sa.text("song_anime.is_rebroadcast OR EXCLUDED.is_rebroadcast"),
            # keep the first non-null notes
            "notes": sa.text("COALESCE(song_anime.notes, EXCLUDED.notes)"),
        },
    )
    db.execute(stmt)


def _row_matches_anime(row: Dict[str, Any], anime: m.Anime) -> bool:
    """Extra guard for title-based search: ensure the hit is really our show."""
    linked = row.get("linked_ids") or {}
    mal_row = linked.get("myanimelist")
    ani_row = linked.get("anilist")
    mal_db = (anime.linked_ids or {}).get("myanimelist")
    ani_db = (anime.linked_ids or {}).get("anilist")

    if mal_db and mal_row and int(mal_db) == int(mal_row):
        return True
    if ani_db and ani_row and int(ani_db) == int(ani_row):
        return True

    # fallback to title comparison
    titles = {
        (anime.title_en or "").lower(),
        (anime.title_romaji or "").lower(),
        (anime.title_jp or "").lower(),
    }
    names = {
        (row.get("animeENName") or "").lower(),
        (row.get("animeJPName") or "").lower(),
    }
    alt = row.get("animeAltName") or []
    names.update([n.lower() for n in alt if isinstance(n, str)])
    return bool(titles & names)


async def import_songs_for_anime(db: Session, anime: m.Anime) -> List[m.Song]:
    """
    Query AniSongDB using MAL id if available, else by anime titles; upsert songs/links/credits.
    Returns the unique list of Song rows linked to this anime after import.
    """
    mal_id = (anime.linked_ids or {}).get("myanimelist")
    results: List[Dict[str, Any]] = []

    if mal_id:
        results = await fetch_by_mal_ids([int(mal_id)])
    else:
        # try each available title
        for t in [anime.title_en, anime.title_romaji, anime.title_jp]:
            if t:
                rows = await search_by_title(t)
                for r in rows:
                    if _row_matches_anime(r, anime):
                        results.append(r)

    if not results:
        return []

    seen_pairs = set()  # (songName, songType, annSongId) to dedupe
    out_songs: List[m.Song] = []

    for r in results:
        song_name = _first(r.get("songName"), r.get("name"))
        song_type_raw = r.get("songType")
        if not song_name or not song_type_raw:
            continue

        use_type, sequence = parse_use_type_and_seq(song_type_raw)
        if use_type not in {"OP", "ED", "IN"}:
            continue

        notes = f"imported from AniSongDB: {song_type_raw}" if song_type_raw else "imported from AniSongDB"

        key = (song_name, song_type_raw, r.get("annSongId"))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        # link-scoped flags & core song fields
        is_dub = r.get("isDub") or False
        is_reb = r.get("isRebroadcast") or False
        audio = _first(r.get("audio"), r.get("HQ"), r.get("MQ")) or ""

        song = _get_or_create_song(db, song_name, audio=audio)

        # credits (prefer arrays; fallback to the single strings)

        artist_objs   = r.get("artists")   or []
        composer_objs = r.get("composers") or []
        arranger_objs = r.get("arrangers") or []

        # ARTISTS
        if artist_objs:
            for a in artist_objs:
                person = _upsert_artist_entity(db, a)   # <-- handles group/memberships
                _ensure_credit_by_id(db, song.id, person.id, "artist")
        else:
            # fallback: string field
            for nm in filter(None, explode_names_from_string(r.get("songArtist"))):
                _ensure_credit(db, song.id, nm, "artist")

        # COMPOSERS
        if composer_objs:
            for a in composer_objs:
                person = _upsert_artist_entity(db, a)   # <-- membership if they’re a group
                _ensure_credit_by_id(db, song.id, person.id, "composer")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songComposer"))):
                _ensure_credit(db, song.id, nm, "composer")

        # ARRANGERS
        if arranger_objs:
            for a in arranger_objs:
                person = _upsert_artist_entity(db, a)   # <-- membership if they’re a group
                _ensure_credit_by_id(db, song.id, person.id, "arranger")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songArranger"))):
                _ensure_credit(db, song.id, nm, "arranger")

        _link_once(
            db,
            song,
            anime,
            use_type=use_type,
            sequence=sequence,
            notes=notes,
            is_dub=is_dub,
            is_rebroadcast=is_reb,
        )

        if song not in out_songs:
            out_songs.append(song)

    db.commit()
    for s in out_songs:
        db.refresh(s)
    return out_songs


async def upsert_person_from_anisongdb_deep(
    db: Session,
    anisongdb_id: int,
    import_songs: bool = True,
) -> Optional[m.People]:
    """
    Import a person/group by AniSongDB id using *song* results:
      - Pull songs via artist_ids_request + composer_ids_request
      - Upsert People (person or group), alt-names, memberships
      - Optionally import all songs/credits/anime links from the results
    Returns the People row (hydrated with memberships).
    """
    aid = int(anisongdb_id)

    rows: List[Dict[str, Any]] = []
    # By-ID pulls (fast & precise)
    try:
        rows += await fetch_songs_by_artist_ids([aid])
    except Exception:
        pass
    # composer rows
    try:
        rows += await fetch_songs_by_composer_ids([aid])
    except Exception:
        pass
    if not rows:
        return None

    # 1) Find the best "Artist" object for the target id from the song rows
    target_artist_obj: Optional[Dict[str, Any]] = None
    for r in rows:
        for a in (r.get("artists") or []):
            if _to_int(a.get("id")) == aid:
                target_artist_obj = a
                break
        if target_artist_obj:
            break
    if not target_artist_obj:
        # Sometimes an id is only present as a composer; try composers
        for r in rows:
            for a in (r.get("composers") or []):
                if _to_int(a.get("id")) == aid:
                    target_artist_obj = a
                    break
            if target_artist_obj:
                break

    # 2) Upsert the *target person* (handles kind, alt_names, groups/members)
    person = _upsert_artist_entity(db, target_artist_obj or {"id": aid, "names": [f"Artist {aid}"]})
    if person.anisongdb_id is None:
        person.anisongdb_id = aid

    if not import_songs:
        db.commit()
        # reload with memberships for response
        return (
            db.query(m.People)
              .options(selectinload(m.People.members), selectinload(m.People.member_of))
              .filter(m.People.id == person.id)
              .first()
        )

    # 3) Deep import: walk through all song entries and persist Songs/Links/Credits
    seen_song_keys: Set[Tuple[Any, Any]] = set()
    out_songs: List[m.Song] = []

    for r in rows:
        # dedupe per (annSongId, songName)
        k = (r.get("annSongId"), r.get("songName"))
        if k in seen_song_keys:
            continue
        seen_song_keys.add(k)

        song_name = r.get("songName") or r.get("name")
        song_type_raw = r.get("songType")
        if not song_name or not song_type_raw:
            continue

        use_type, sequence = parse_use_type_and_seq(song_type_raw)
        if use_type not in {"OP", "ED", "IN"}:
            continue

        is_dub = bool(r.get("isDub"))
        is_reb = bool(r.get("isRebroadcast"))
        audio = (r.get("audio") or r.get("HQ") or r.get("MQ") or "")  # prefer HQ/MQ fallback
        notes = f"imported from AniSongDB: {song_type_raw}"

        song = _get_or_create_song(db, song_name, audio=audio)
        anime = _get_or_create_anime_from_row(db, r)

        _link_once(
            db, song, anime,
            use_type=use_type, sequence=sequence, notes=notes,
            is_dub=is_dub, is_rebroadcast=is_reb,
        )

        # CREDIT everyone on the row (so target person will be among them)
        artist_objs   = r.get("artists")   or []
        composer_objs = r.get("composers") or []
        arranger_objs = r.get("arrangers") or []

        if artist_objs:
            for a in artist_objs:
                p = _upsert_artist_entity(db, a)     # handles group/memberships
                _ensure_credit_by_id(db, song.id, p.id, "artist")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songArtist"))):
                _ensure_credit(db, song.id, nm, "artist")

        if composer_objs:
            for a in composer_objs:
                p = _upsert_artist_entity(db, a)
                _ensure_credit_by_id(db, song.id, p.id, "composer")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songComposer"))):
                _ensure_credit(db, song.id, nm, "composer")

        if arranger_objs:
            for a in arranger_objs:
                p = _upsert_artist_entity(db, a)
                _ensure_credit_by_id(db, song.id, p.id, "arranger")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songArranger"))):
                _ensure_credit(db, song.id, nm, "arranger")

        if song not in out_songs:
            out_songs.append(song)

    db.commit()

    # Reload person with memberships for a rich response
    person = (
        db.query(m.People)
          .options(selectinload(m.People.members), selectinload(m.People.member_of))
          .filter(m.People.id == person.id)
          .first()
    )
    return person


async def import_songs_for_person(
    db: Session,
    person: m.People,
    *,
    roles: Optional[Set[str]] = None,
) -> List[m.Song]:
    """
    Import songs where this person participates in any of the given roles.
    roles defaults to {"artist","composer","arranger"}.
    """
    role_set: Set[str] = set(roles or {"artist", "composer", "arranger"})
    results: List[Dict[str, Any]] = []

    # 1) ID-based pulls (fast, precise)
    if person.anisongdb_id is not None:
        if "artist" in role_set:
            results += await fetch_songs_by_artist_ids([int(person.anisongdb_id)])
        if "composer" in role_set:
            results += await fetch_songs_by_composer_ids([int(person.anisongdb_id)])
        # No arranger-ids endpoint in the spec; arranger coverage comes from rows we already pulled.

    # 2) Fallback by name(s) using /api/search_request
    if not results:
        seen = set()
        for name in [person.primary_name, *(person.alt_names or [])]:
            if not name:
                continue
            rows = await search_songs_for_person(name, role_set)
            for r in rows or []:
                key = (r.get("annSongId"), r.get("songName"), r.get("animeENName"))
                if key in seen:
                    continue
                seen.add(key)
                results.append(r)

    if not results:
        return []

    # 3) Persist songs, anime-links, credits, memberships (idempotent)
    out_songs: List[m.Song] = []
    seen_song_keys: Set[Tuple[Any, Any]] = set()

    for r in results:
        k = (r.get("annSongId"), r.get("songName"))
        if k in seen_song_keys:
            continue
        seen_song_keys.add(k)

        song_name = r.get("songName") or r.get("name")
        raw = r.get("songType")
        if not song_name or not raw:
            continue

        use_type, sequence = parse_use_type_and_seq(raw)
        if use_type not in {"OP", "ED", "IN"}:
            continue

        is_dub = bool(r.get("isDub"))
        is_rebroadcast = bool(r.get("isRebroadcast"))
        audio = r.get("audio") or r.get("HQ") or r.get("MQ") or ""
        notes = f"imported from AniSongDB: {raw}"

        song = _get_or_create_song(db, song_name, audio=audio)
        anime = _get_or_create_anime_from_row(db, r)

        _link_once(
            db, song, anime,
            use_type=use_type, sequence=sequence, notes=notes,
            is_dub=is_dub, is_rebroadcast=is_rebroadcast,
        )

        # CREDIT everyone present on the row (ensures the requested person is linked)
        artist_objs   = r.get("artists")   or []
        composer_objs = r.get("composers") or []
        arranger_objs = r.get("arrangers") or []

        if artist_objs:
            for a in artist_objs:
                p = _upsert_artist_entity(db, a)
                _ensure_credit_by_id(db, song.id, p.id, "artist")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songArtist"))):
                _ensure_credit(db, song.id, nm, "artist")

        if composer_objs:
            for a in composer_objs:
                p = _upsert_artist_entity(db, a)
                _ensure_credit_by_id(db, song.id, p.id, "composer")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songComposer"))):
                _ensure_credit(db, song.id, nm, "composer")

        if arranger_objs:
            for a in arranger_objs:
                p = _upsert_artist_entity(db, a)
                _ensure_credit_by_id(db, song.id, p.id, "arranger")
        else:
            for nm in filter(None, explode_names_from_string(r.get("songArranger"))):
                _ensure_credit(db, song.id, nm, "arranger")

        if song not in out_songs:
            out_songs.append(song)

    db.commit()
    for s in out_songs:
        db.refresh(s)
    return out_songs
