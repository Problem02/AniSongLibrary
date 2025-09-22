from __future__ import annotations
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.db.session import SessionLocal
from app.db import models as m
from app.db import schemas as s
from app.clients.anisongdb import AniSongDBNotConfigured
from app.services.anisong_importer import import_songs_for_anime

router = APIRouter(prefix="/songs", tags=["songs"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _get_anime_or_404(db: Session, anime_id: uuid.UUID) -> m.Anime:
    row = db.query(m.Anime).filter(m.Anime.id == anime_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="anime_not_found")
    return row

@router.get("/by-anime/{anime_id}", response_model=List[s.Song])
async def get_songs_by_anime(anime_id: uuid.UUID,
                             import_if_missing: bool = True,
                             db: Session = Depends(get_db)):
    anime = _get_anime_or_404(db, anime_id)

    has_any = db.query(exists().where(m.SongAnime.anime_id == anime_id)).scalar()
    if not has_any and import_if_missing:
        try:
            await import_songs_for_anime(db, anime)
        except AniSongDBNotConfigured:
            db.rollback()
            raise HTTPException(status_code=502, detail={"error":"anisongdb_not_configured"})
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=502, detail={"error":"anisongdb_import_failed","message":str(e)})

    # now the session is clean; this select won't hit InFailedSqlTransaction
    songs = (
        db.query(m.Song)
          .join(m.SongAnime, m.SongAnime.song_id == m.Song.id)
          .filter(m.SongAnime.anime_id == anime_id)
          .order_by(m.Song.created_at.desc())
          .all()
    )
    return songs
