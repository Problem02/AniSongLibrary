from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.db import models as m
from app.db import schemas as s
from app.clients.anilist import fetch_anime_by_id
from app.services.anisong_importer import import_song_and_anime_by_amq_song_id
from app.clients.anisongdb import AniSongDBNotConfigured

router = APIRouter(prefix="/anime", tags=["anime"])

# --- deps --------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --- helpers -----------------------------------------------------------------
SEASON_MAP = {"WINTER": "Winter", "SPRING": "Spring", "SUMMER": "Summer", "FALL": "Fall"}

def _map_anilist_media_to_anime_fields(media: dict) -> dict:
    title = media.get("title") or {}
    cover = media.get("coverImage") or {}
    linked = {}
    if media.get("id") is not None:
        linked["anilist"] = media["id"]
    if media.get("idMal") is not None:
        linked["myanimelist"] = media["idMal"]
    if media.get("synonyms"):
        linked["synonyms"] = media["synonyms"]

    return {
        "title_en": title.get("english"),
        "title_jp": title.get("native"),
        "title_romaji": title.get("romaji"),
        "season": SEASON_MAP.get(media.get("season") or "", None),
        "year": media.get("seasonYear"),
        "type": media.get("format"),
        "cover_image_url": cover.get("extraLarge") or cover.get("large") or cover.get("medium"),
        "linked_ids": linked,
    }


def _get_by_anilist_id(db: Session, anilist_id: int) -> Optional[m.Anime]:
    try:
        row = (
            db.query(m.Anime)
              .filter(or_(
                  m.Anime.linked_ids.contains({"anilist": anilist_id}),
                  m.Anime.linked_ids.contains({"anilist": str(anilist_id)}),
              ))
              .first()
        )
        if row:
            return row
    except Exception:
        db.rollback()  # <-- clear the failed transaction before any further queries

    # Safe Python-side scan fallback (won't 500)
    for a in db.query(m.Anime.id, m.Anime.linked_ids).all():
        v = (a.linked_ids or {}).get("anilist")
        if v is not None and str(v) == str(anilist_id):
            return db.query(m.Anime).filter(m.Anime.id == a.id).first()
    return None


def _get_or_404(db: Session, anime_id: uuid.UUID) -> m.Anime:
    row = db.query(m.Anime).filter(m.Anime.id == anime_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="anime_not_found")
    return row


# --- routes: CRUD ------------------------------------------------------------
@router.get("", response_model=list[s.Anime], response_model_exclude_none=True)
def list_anime(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="case-insensitive search across titles"),
    season: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    query = db.query(m.Anime)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (m.Anime.title_en.ilike(like)) |
            (m.Anime.title_jp.ilike(like)) |
            (m.Anime.title_romaji.ilike(like))
        )
    if season:
        query = query.filter(m.Anime.season == season)
    if year:
        query = query.filter(m.Anime.year == year)
    if type:
        query = query.filter(m.Anime.type == type)
    rows = query.order_by(m.Anime.created_at.desc()).offset(skip).limit(limit).all()
    return rows


@router.get("/{anime_id:uuid}", response_model=s.Anime, response_model_exclude_none=True)
def get_anime(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, anime_id)


@router.patch("/{anime_id:uuid}", response_model=s.Anime)
def patch_anime(anime_id: uuid.UUID, payload: s.AnimeUpdate, db: Session = Depends(get_db)):
    row = _get_or_404(db, anime_id)
    data = payload.model_dump(exclude_unset=True)

    # merge linked_ids instead of clobbering (if provided)
    if "linked_ids" in data and data["linked_ids"] is not None:
        merged = dict(row.linked_ids or {})
        merged.update(data["linked_ids"])
        row.linked_ids = merged
        data.pop("linked_ids")

    for field, value in data.items():
        setattr(row, field, value)
        
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{anime_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anime(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    row = _get_or_404(db, anime_id)
    db.delete(row)
    db.commit()
    return None


# --- routes: import/upsert from AniList -------------------------------------
@router.post("/import/anilist/{anilist_id}", response_model=s.Anime, status_code=status.HTTP_201_CREATED)
async def import_anime_from_anilist(anilist_id: int, db: Session = Depends(get_db)):
    media = await fetch_anime_by_id(anilist_id)
    if not media:
        raise HTTPException(status_code=404, detail="anilist_media_not_found")

    fields = _map_anilist_media_to_anime_fields(media)
    existing = _get_by_anilist_id(db, anilist_id)

    if existing:
        # update in place (idempotent upsert)
        for k, v in fields.items():
            if k == "linked_ids":
                merged = dict(existing.linked_ids or {})
                merged.update(v or {})
                setattr(existing, k, merged)
            else:
                setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing

    # create new
    new_row = m.Anime(**fields)
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


# --- routes: songs for an anime (appearances) --------------------------------
@router.get(
    "/{anime_id:uuid}/songs",
    response_model=list[s.AnimeSongAppearance],
    response_model_exclude_none=True,
)
def list_anime_songs(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    _ = _get_or_404(db, anime_id)
    rows = (
        db.query(m.SongAnime, m.Song)
          .join(m.Song, m.Song.id == m.SongAnime.song_id)
          .options(
              # eager load nested structures your s.Song schema will serialize
              selectinload(m.Song.anime_links).selectinload(m.SongAnime.anime),
              selectinload(m.Song.credits).selectinload(m.SongArtist.people),
          )
          .filter(m.SongAnime.anime_id == anime_id)
          .order_by(m.SongAnime.sequence.nulls_last(), m.SongAnime.use_type)
          .all()
    )

    out: list[s.AnimeSongAppearance] = []
    for link, song in rows:
        out.append(
            s.AnimeSongAppearance(
                link_id=link.id,
                song=s.Song.model_validate(song),  # full Song object (with credits/anime_links)
                use_type=link.use_type,
                sequence=link.sequence,
                notes=link.notes,
                is_dub=link.is_dub,
                is_rebroadcast=link.is_rebroadcast,
            )
        )
    return out


@router.post("/import/by-amq-song/{amq_song_id:int}",
    response_model=list[s.Anime],
    response_model_exclude_none=True,
)
async def import_anime_by_amq_song(amq_song_id: int, db: Session = Depends(get_db)):
    """
    Given an AMQ song id:
      - Create the Song if it doesn't exist (and set amq_song_id if your model has it)
      - Upsert the Anime entries the song appears in
      - Link them (populating song.anime_links)
    Returns the distinct list of Anime rows touched.
    """
    try:
        song, animes = await import_song_and_anime_by_amq_song_id(db, amq_song_id)
    except AniSongDBNotConfigured:
        db.rollback()
        raise HTTPException(status_code=502, detail={"error": "anisongdb_not_configured"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail={"error": "anisongdb_import_failed", "message": str(e)})

    if not song:
        raise HTTPException(status_code=404, detail="amq_song_not_found")

    return animes