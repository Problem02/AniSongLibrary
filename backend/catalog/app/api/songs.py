from __future__ import annotations
import uuid
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import exists

from app.db.session import SessionLocal
from app.db import models as m
from app.db import schemas as s
from app.clients.anisongdb import AniSongDBNotConfigured
from app.services.anisong_importer import import_songs_for_anime, import_songs_for_person

router = APIRouter(prefix="/songs", tags=["songs"])

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
def _get_song_or_404(db: Session, song_id: uuid.UUID) -> m.Song:
    row = (
        db.query(m.Song)
          .options(
              selectinload(m.Song.anime_links).selectinload(m.SongAnime.anime),
              selectinload(m.Song.credits).selectinload(m.SongArtist.people),
          )
          .filter(m.Song.id == song_id)
          .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="song_not_found")
    return row

def _get_anime_or_404(db: Session, anime_id: uuid.UUID) -> m.Anime:
    row = db.query(m.Anime).filter(m.Anime.id == anime_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="anime_not_found")
    return row

def _get_person_or_404(db: Session, person_id: uuid.UUID) -> m.People:
    row = db.query(m.People).filter(m.People.id == person_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="people_not_found")
    return row

def _parse_roles(roles: Optional[str]) -> Set[str]:
    allowed = {"artist", "composer", "arranger"}
    if not roles:
        return allowed
    parts = {p.strip().lower() for p in roles.split(",")}
    picked = allowed & parts
    return picked or allowed


# --- routes: CRUD ------------------------------------------------------------
@router.get("", response_model=List[s.Song], response_model_exclude_none=True)
def list_songs(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="case-insensitive search by song name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    query = (
        db.query(m.Song)
          .options(
              selectinload(m.Song.anime_links).selectinload(m.SongAnime.anime),
              selectinload(m.Song.credits).selectinload(m.SongArtist.people),
          )
          .order_by(m.Song.created_at.desc())
    )
    if q:
        like = f"%{q}%"
        query = query.filter(m.Song.name.ilike(like))
    rows = query.offset(skip).limit(limit).all()
    return rows


@router.get("/{song_id:uuid}", response_model=s.Song, response_model_exclude_none=True)
def get_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_song_or_404(db, song_id)


# --- routes: songs by anime --------------------------------
@router.get("/by-anime/{anime_id:uuid}", response_model=List[s.Song], response_model_exclude_none=True)
async def get_songs_by_anime(
    anime_id: uuid.UUID,
    import_if_missing: bool = True,
    db: Session = Depends(get_db),
):
    anime = _get_anime_or_404(db, anime_id)

    has_any = db.query(exists().where(m.SongAnime.anime_id == anime_id)).scalar()
    if not has_any and import_if_missing:
        try:
            await import_songs_for_anime(db, anime)
        except AniSongDBNotConfigured:
            db.rollback()
            raise HTTPException(status_code=502, detail={"error": "anisongdb_not_configured"})
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=502, detail={"error": "anisongdb_import_failed", "message": str(e)})

    # Eager-load nested pieces required by s.Song:
    #   - song.anime_links (+ each link.anime)
    #   - song.credits (+ each credit.people)
    songs = (
    db.query(m.Song)
      .join(m.SongAnime, m.SongAnime.song_id == m.Song.id)
      .options(
          selectinload(m.Song.anime_links).selectinload(m.SongAnime.anime),
          selectinload(m.Song.credits).selectinload(m.SongArtist.people),
      )
      .filter(m.SongAnime.anime_id == anime_id)
      .order_by(m.Song.created_at.desc())
      .distinct()   # ← Checks for duplicates
      .all()
    )
    return songs


# --- routes: songs by person --------------------------------
@router.get("/by-person/{person_id:uuid}", response_model=List[s.Song], response_model_exclude_none=True)
async def get_songs_by_person(
    person_id: uuid.UUID,
    roles: Optional[str] = Query(None, description="comma-separated: artist,composer,arranger"),
    import_if_missing: bool = True,
    db: Session = Depends(get_db),
):
    """
    Return songs where this person is credited with any of the selected roles.
    On empty result and import_if_missing=true, pull from AniSongDB using the person's
    anisongdb_id (preferred) or name/alt-names, then re-query.
    """
    person = _get_person_or_404(db, person_id)
    role_set = _parse_roles(roles)

    def _query():
        return (
            db.query(m.Song)
              .join(m.SongArtist, m.SongArtist.song_id == m.Song.id)
              .options(
                  selectinload(m.Song.anime_links).selectinload(m.SongAnime.anime),
                  selectinload(m.Song.credits).selectinload(m.SongArtist.people),
              )
              .filter(m.SongArtist.people_id == person_id, m.SongArtist.role.in_(role_set))
              .order_by(m.Song.created_at.desc())
              .distinct()   # dedupe across multiple credits
              .all()
        )

    songs = _query()
    if not songs and import_if_missing:
        await import_songs_for_person(db, person, roles=role_set)
        songs = _query()

    return songs
