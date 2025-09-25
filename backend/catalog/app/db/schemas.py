from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Enums as constrained string types ---------------------------------------

SongType = Literal["OP", "ED", "IN"]
CreditRole = Literal["artist", "composer", "arranger"]


# --- Briefs / Refs -----------------------------------------------------------

class PeopleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    primary_name: str
    image_url: Optional[str] = None
    kind: Literal["person", "group"]


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
    is_dub: bool
    is_rebroadcast: bool
    sequence: Optional[int] = None
    notes: Optional[str] = None

class SongAnimeLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    anime: Anime
    use_type: SongType
    is_dub: bool
    is_rebroadcast: bool
    sequence: Optional[int] = None
    notes: Optional[str] = None


# --- Song schemas ------------------------------------------------------------

class SongCreate(BaseModel):
    name: str
    audio: str
    anime_links: List[SongAnimeLinkIn] = []
    credits: List[SongCreditIn] = []

class SongUpdate(BaseModel):
    name: Optional[str] = None
    audio: Optional[str] = None
    # replace-all semantics when provided
    anime_links: Optional[List[SongAnimeLinkIn]] = None
    credits: Optional[List[SongCreditIn]] = None

class Song(BaseModel):
    """Read schema (response)"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    amq_song_id: int | None = None
    name: str
    audio: str
    anime_links: List[SongAnimeLinkOut]
    credits: List[SongCreditOut]
    created_at: datetime
    updated_at: datetime


# --- People schemas --------------------------------------------

class People(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    anisongdb_id: Optional[int] = None
    kind: Literal["person", "group"]
    primary_name: str
    alt_names: List[str] = []
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
class PeopleUpdate(BaseModel):
    # all optional so PATCH can be partial
    primary_name: Optional[str] = None
    alt_names: Optional[List[str]] = None
    image_url: Optional[str] = None
    kind: Optional[Literal["person", "group"]] = None
    anisongdb_id: Optional[int] = None
    
class PeopleDetail(People):
    # richer view that includes memberships
    members: List[PeopleBrief] = []
    member_of: List[PeopleBrief] = []

    
# --- Anime schemas --------------------------------

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

class AnimeUpdate(BaseModel):
    title_en: Optional[str] = None
    title_jp: Optional[str] = None
    title_romaji: Optional[str] = None
    season: Optional[str] = None    # "Spring" | "Summer" | "Fall" | "Winter"
    year: Optional[int] = None
    type: Optional[str] = None      # TV | MOVIE | ONA | ...
    cover_image_url: Optional[str] = None
    linked_ids: Optional[dict] = None  # allow merging on PATCH

class AnimeSongAppearance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    link_id: UUID
    song: Song
    use_type: SongType
    is_dub: bool
    is_rebroadcast: bool
    sequence: Optional[int] = None
    notes: Optional[str] = None
