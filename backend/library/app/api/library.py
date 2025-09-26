from __future__ import annotations

import uuid
from typing import List, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
import app.db.models as m
import app.db.schemas as s
from app.core.config import settings

router = APIRouter(prefix="/library", tags=["library"])

# ---------------------------------------------------------------------------
# deps

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

bearer = HTTPBearer(auto_error=False)

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")
    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,           
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=60,
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="invalid_audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="invalid_issuer")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid_token")

def current_user_id(claims: dict = Depends(require_auth)) -> uuid.UUID:
    try:
        return uuid.UUID(claims["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_subject")

# ---------------------------------------------------------------------------
# helpers

_NAMESPACE = uuid.NAMESPACE_URL

def _rating_id(user_id: uuid.UUID, song_id: uuid.UUID) -> uuid.UUID:
    """Deterministic UUID over (user_id, song_id) so routes can use a stable id."""
    return uuid.uuid5(_NAMESPACE, f"library:{user_id}:{song_id}")

def _to_schema(user_id: uuid.UUID, row: m.LibraryEntry) -> s.Rating:
    return s.Rating(
        id=_rating_id(user_id, row.song_id),
        user_id=user_id,
        song_id=row.song_id,
        amq_song_id=row.amq_song_id,
        score=row.score,
        is_favorite=row.is_favorite,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

def _get_by_song_or_404(db: Session, user_id: uuid.UUID, song_id: uuid.UUID) -> m.LibraryEntry:
    row = (
        db.query(m.LibraryEntry)
        .filter(m.LibraryEntry.user_id == user_id, m.LibraryEntry.song_id == song_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="rating_not_found")
    return row

def _get_by_rating_id_or_404(db: Session, user_id: uuid.UUID, rating_id: uuid.UUID) -> m.LibraryEntry:
    # Scan this user's rows and match the derived id; swap for a direct lookup if you add a surrogate key.
    rows = (
        db.query(m.LibraryEntry)
        .filter(m.LibraryEntry.user_id == user_id)
        .order_by(m.LibraryEntry.updated_at.desc())
        .all()
    )
    for r in rows:
        if _rating_id(user_id, r.song_id) == rating_id:
            return r
    raise HTTPException(status_code=404, detail="rating_not_found")

# ---------------------------------------------------------------------------
# routes

@router.get("", response_model=List[s.Rating], response_model_exclude_none=True)
def get_library(
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    is_favorite: Optional[bool] = None,
):
    """
    Get all library entries for the current user (paged).
    Optional filters: min_score, is_favorite.
    """
    q = db.query(m.LibraryEntry).filter(m.LibraryEntry.user_id == user_id)
    if min_score is not None:
        q = q.filter(m.LibraryEntry.score >= min_score)
    if is_favorite is not None:
        q = q.filter(m.LibraryEntry.is_favorite == is_favorite)
    rows = q.order_by(m.LibraryEntry.updated_at.desc()).offset(skip).limit(limit).all()
    return [_to_schema(user_id, r) for r in rows]

@router.get("/{rating_id:uuid}", response_model=s.Rating, response_model_exclude_none=True)
def get_rating(
    rating_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    """Get a single rating by its rating_id (derived from user_id+song_id)."""
    row = _get_by_rating_id_or_404(db, user_id, rating_id)
    return _to_schema(user_id, row)

@router.get("/by-song/{song_id:uuid}", response_model=s.Rating, response_model_exclude_none=True)
def get_rating_by_song_id(
    song_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    """Get the user's rating for a given song_id."""
    row = _get_by_song_or_404(db, user_id, song_id)
    return _to_schema(user_id, row)

@router.post("", response_model=s.Rating, response_model_exclude_none=True, status_code=201)
def create_rating(
    payload: s.RatingCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    """Create a library entry for this user+song; 409 if one already exists."""
    exists = (
        db.query(m.LibraryEntry)
        .filter(m.LibraryEntry.user_id == user_id, m.LibraryEntry.song_id == payload.song_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="rating_already_exists")

    row = m.LibraryEntry(
        user_id=user_id,
        song_id=payload.song_id,
        amq_song_id=payload.amq_song_id,
        score=payload.score,
        is_favorite=payload.is_favorite,
        note=payload.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_schema(user_id, row)

@router.patch("/{rating_id:uuid}", response_model=s.Rating, response_model_exclude_none=True)
def update_rating(
    rating_id: uuid.UUID,
    payload: s.RatingUpdate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    """Update score/is_favorite/note of the user's rating (by rating_id)."""
    row = _get_by_rating_id_or_404(db, user_id, rating_id)

    if payload.score is not None:
        row.score = payload.score
    if payload.is_favorite is not None:
        row.is_favorite = payload.is_favorite
    if payload.note is not None:
        row.note = payload.note

    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_schema(user_id, row)

@router.delete("/{rating_id:uuid}", status_code=204)
def delete_rating(
    rating_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    """Delete the user's rating (by rating_id)."""
    row = _get_by_rating_id_or_404(db, user_id, rating_id)
    db.delete(row)
    db.commit()
    return
