from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
import sqlalchemy as sa
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_

from app.db.session import SessionLocal
from app.db import models as m
from app.db import schemas as s
from app.services.anisong_importer import upsert_person_from_anisongdb_deep

router = APIRouter(prefix="/people", tags=["people"])

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

def _get_or_404(db: Session, people_id: uuid.UUID) -> m.People:
    row = db.query(m.People).filter(m.People.id == people_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="people_not_found")
    return row

# --- routes ------------------------------------------------------------------

@router.get("", response_model=List[s.People], response_model_exclude_none=True)
def list_people(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="case-insensitive match on primary/alt names"),
    kind: Optional[str] = Query(None, pattern="^(person|group)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    query = db.query(m.People)

    if q:
        like = f"%{q}%"
        # primary_name ILIKE or ANY(alt_names) ILIKE
        query = query.filter(
            or_(
                m.People.primary_name.ilike(like),
                m.People.alt_names.any(sa.text(f"ILIKE '{like}'"))  # Postgres ARRAY any + ILIKE
            )
        )
    if kind:
        query = query.filter(m.People.kind == kind)

    rows = query.order_by(m.People.created_at.desc()).offset(skip).limit(limit).all()
    return rows


@router.get("/{people_id:uuid}", response_model=s.PeopleDetail, response_model_exclude_none=True)
def get_person(people_id: uuid.UUID, db: Session = Depends(get_db)):
    row = (
        db.query(m.People)
          .options(
              selectinload(m.People.members),
              selectinload(m.People.member_of),
          )
          .filter(m.People.id == people_id)
          .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="people_not_found")

    # Pydantic v2 will read attributes from ORM objects (from_attributes=True)
    # and coerce list[People] -> list[PeopleBrief] automatically.
    return s.PeopleDetail.model_validate(row)


@router.patch("/{people_id:uuid}", response_model=s.People)
def update_person(
    people_id: uuid.UUID,
    payload: s.PeopleUpdate,
    db: Session = Depends(get_db),
):
    row = _get_or_404(db, people_id)
    data = payload.model_dump(exclude_unset=True)

    # Normalize & replace alt_names if provided
    if "alt_names" in data and data["alt_names"] is not None:
        names: list[str] = []
        for n in data["alt_names"]:
            if not n:
                continue
            n = n.strip()
            if n and n not in names:
                names.append(n)
        row.alt_names = names
        data.pop("alt_names")
        
    if "anisongdb_id" in data:
        v = data.pop("anisongdb_id")
        row.anisongdb_id = int(v) if v is not None else None

    # Set the rest directly (primary_name, image_url, kind)
    for field, value in data.items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return row


# --- routes: import/upsert from AnisongDB -------------------------------------
@router.post("/import/anisongdb/{anisongdb_id}", response_model=s.PeopleDetail, status_code=status.HTTP_200_OK)
async def import_person_from_anisongdb(
    anisongdb_id: int,
    import_songs: bool = Query(True, description="Also import all songs/credits/anime links involving this person"),
    db: Session = Depends(get_db),
):
    person = await upsert_person_from_anisongdb_deep(db, anisongdb_id, import_songs=import_songs)
    if not person:
        raise HTTPException(status_code=404, detail="anisongdb_person_not_found")
    return s.PeopleDetail.model_validate(person)
