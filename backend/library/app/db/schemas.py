from typing import Annotated, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

Score = Annotated[int, Field(ge=0, le=100)]

class RatingCreate(BaseModel):
    song_id: UUID
    amq_song_id: Optional[int] = None 
    score: Score
    is_favorite: bool = False
    note: Optional[str] = None

class RatingUpdate(BaseModel):
    score: Optional[Score] = None
    is_favorite: Optional[bool] = None
    note: Optional[str] = None

class Rating(BaseModel):
    id: UUID
    user_id: UUID
    song_id: UUID
    amq_song_id: int | None = None
    score: Score
    is_favorite: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime
