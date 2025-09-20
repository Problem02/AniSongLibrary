from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

def uid() -> str:
    return str(uuid.uuid4())


class LibraryEntry(Base):
    __tablename__ = "library_entries"
    user_id = Column(String, primary_key=True)
    entity_type = Column(String, primary_key=True) # anime|song
    entity_id = Column(String, primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())


class Rating(Base):
    __tablename__ = "ratings"
    user_id = Column(String, primary_key=True)
    song_id = Column(String, primary_key=True)
    score = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class RatingAggregate(Base):
    __tablename__ = "rating_aggregates"
    anime_id = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)
    rated_count = Column(Integer, nullable=False, default=0)
    total_songs = Column(Integer, nullable=False, default=0)
    avg_score = Column(Integer, nullable=True)
    fully_rated = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())