from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db import models as m
from app.clients.anilist import fetch_anime_by_id

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

# --- schemas (reuse your shared ones where possible) -------------------------
class AnimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title_en: Optional[str] = None
    title_jp: Optional[str] = None
    title_romaji: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None
    cover_image_url: Optional[str] = None

class AnimeUpdate(BaseModel):
    title_en: Optional[str] = None
    title_jp: Optional[str] = None
    title_romaji: Optional[str] = None
    season: Optional[str] = None   # "Spring" | "Summer" | "Fall" | "Winter"
    year: Optional[int] = None
    type: Optional[str] = None     # TV | MOVIE | ONA | ...
    cover_image_url: Optional[str] = None

class AnimeSongAppearance(BaseModel):
    """Return songs for this anime, with per-appearance data."""
    model_config = ConfigDict(from_attributes=True)
    link_id: uuid.UUID
    song_id: uuid.UUID
    name: str
    use_type: str
    sequence: Optional[int] = None
    notes: Optional[str] = None

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
@router.get("", response_model=list[AnimeRead])
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

@router.get("/{anime_id}", response_model=AnimeRead)
def get_anime(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, anime_id)

@router.patch("/{anime_id}", response_model=AnimeRead)
def patch_anime(anime_id: uuid.UUID, payload: AnimeUpdate, db: Session = Depends(get_db)):
    row = _get_or_404(db, anime_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row

@router.delete("/{anime_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anime(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    row = _get_or_404(db, anime_id)
    db.delete(row)
    db.commit()
    return None

# --- routes: import/upsert from AniList -------------------------------------
@router.post("/import/anilist/{anilist_id}", response_model=AnimeRead, status_code=status.HTTP_201_CREATED)
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
@router.get("/{anime_id}/songs", response_model=list[AnimeSongAppearance])
def list_anime_songs(anime_id: uuid.UUID, db: Session = Depends(get_db)):
    _ = _get_or_404(db, anime_id)
    rows = (
        db.query(m.SongAnime, m.Song)
        .join(m.Song, m.Song.id == m.SongAnime.song_id)
        .filter(m.SongAnime.anime_id == anime_id)
        .order_by(m.SongAnime.sequence.nulls_last(), m.SongAnime.use_type)
        .all()
    )
    out: List[AnimeSongAppearance] = []
    for link, song in rows:
        out.append(AnimeSongAppearance(
            link_id=link.id,
            song_id=song.id,
            name=song.name,
            use_type=link.use_type,
            sequence=link.sequence,
            notes=link.notes,
        ))
    return out
