from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship
import enum, uuid

Base = declarative_base()

def uid() -> str:
    return str(uuid.uuid4())

class SongType(str, enum.Enum):
    OP = "OP"
    ED = "ED"
    IN = "IN"

class Anime(Base):
    __tablename__ = "anime"
    id = Column(String, primary_key=True, default=uid)
    title_en = Column(String, nullable=True)
    title_jp = Column(String, nullable=True)
    season = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    cover_image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Artist(Base):
    __tablename__ = "artist"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)

class Song(Base):
    __tablename__ = "song"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    type = Column(Enum(SongType), nullable=False)
    anime_id = Column(String, ForeignKey("anime.id"), nullable=False)
    anime = relationship("Anime")

class SongArtist(Base):
    __tablename__ = "song_artists"
    song_id = Column(String, ForeignKey("song.id"), primary_key=True)
    artist_id = Column(String, ForeignKey("artist.id"), primary_key=True)
    role = Column(String, nullable=True)

class ExternalLink(Base):
    __tablename__ = "external_links"
    entity_type = Column(String, primary_key=True)
    entity_id = Column(String, primary_key=True)
    provider = Column(String, primary_key=True)
    provider_id = Column(String, nullable=False)