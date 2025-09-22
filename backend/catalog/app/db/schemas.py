from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Enums as constrained string types ---------------------------------------

SongType = Literal["OP", "ED", "IN"]
CreditRole = Literal["artist", "composer", "arranger"]

# --- Briefs / Refs -----------------------------------------------------------

class AnimeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title_en: Optional[str] = None
    title_jp: Optional[str] = None
    title_romaji: Optional[str] = None

class PeopleBrief(BaseModel):
    """Minimal person reference; maps People.primary_name -> name."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    name: str = Field(alias="primary_name")

# --- Credits -----------------------------------------------------------------

class SongCreditIn(BaseModel):
    people_id: UUID
    role: CreditRole

class SongCreditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: CreditRole
    people: PeopleBrief  # comes from SongArtist.people relationship

# --- Song<->Anime link (association object) ----------------------------------

class SongAnimeLinkIn(BaseModel):
    anime_id: UUID
    use_type: SongType
    sequence: Optional[int] = None
    notes: Optional[str] = None

class SongAnimeLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    anime: AnimeBrief
    use_type: SongType
    sequence: Optional[int] = None
    notes: Optional[str] = None

# --- Song schemas ------------------------------------------------------------

class SongCreate(BaseModel):
    name: str
    audio: str
    is_dub: bool = False
    is_rebroadcast: bool = False
    anime_links: List[SongAnimeLinkIn] = []
    credits: List[SongCreditIn] = []

class SongUpdate(BaseModel):
    name: Optional[str] = None
    audio: Optional[str] = None
    is_dub: Optional[bool] = None
    is_rebroadcast: Optional[bool] = None
    # replace-all semantics when provided
    anime_links: Optional[List[SongAnimeLinkIn]] = None
    credits: Optional[List[SongCreditIn]] = None

class Song(BaseModel):
    """Read schema (response)"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    audio: str
    is_dub: bool
    is_rebroadcast: bool
    anime_links: List[SongAnimeLinkOut]
    credits: List[SongCreditOut]
    created_at: datetime
    updated_at: datetime

# --- Anime & People read schemas --------------------------------------------

class Anime(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title_en: Optional[str] = None
    title_jp: Optional[str] = None
    title_romaji: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None
    cover_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class People(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: Literal["person", "group"]
    primary_name: str
    alt_names: List[str] = []
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
