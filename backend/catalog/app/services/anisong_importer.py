from __future__ import annotations

from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import models as m
from app.clients.anisongdb import (
    fetch_by_mal_ids,
    search_by_title,
    parse_use_type_and_seq,
    explode_names_from_string,
)


def _first(*vals):
    for v in vals:
        if v:
            return v
    return None


def _get_or_create_person(db: Session, name: str) -> m.People:
    row = db.query(m.People).filter(m.People.primary_name == name).first()
    if row:
        return row
    row = m.People(kind="person", primary_name=name, alt_names=[], external_links={})
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


def _ensure_credit(db: Session, song_id, people_name: str, role: str) -> None:
    p = _get_or_create_person(db, people_name)
    stmt = pg_insert(m.SongArtist.__table__).values(song_id=song_id, people_id=p.id, role=role)
    # PK is (song_id, people_id, role) -> ignore duplicates safely
    stmt = stmt.on_conflict_do_nothing(index_elements=["song_id", "people_id", "role"])
    db.execute(stmt)


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
        def name_from_artist_obj(a: Dict[str, Any]) -> Optional[str]:
            names = a.get("names") or []
            return names[0] if names else None

        artists = [name_from_artist_obj(a) for a in (r.get("artists") or [])]
        composers = [name_from_artist_obj(a) for a in (r.get("composers") or [])]
        arrangers = [name_from_artist_obj(a) for a in (r.get("arrangers") or [])]

        if not artists:
            artists = explode_names_from_string(r.get("songArtist"))
        if not composers:
            composers = explode_names_from_string(r.get("songComposer"))
        if not arrangers:
            arrangers = explode_names_from_string(r.get("songArranger"))

        for n in filter(None, artists):
            _ensure_credit(db, song.id, n, "artist")
        for n in filter(None, composers):
            _ensure_credit(db, song.id, n, "composer")
        for n in filter(None, arrangers):
            _ensure_credit(db, song.id, n, "arranger")

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
