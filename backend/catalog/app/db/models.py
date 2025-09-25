import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import UUID, ForeignKey, Index, UniqueConstraint, ARRAY
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

# Reference existing pg enums created by Alembic; do NOT auto-create types here
song_type = postgresql.ENUM("OP", "ED", "IN", name="song_type", create_type=False)
song_credit_role = postgresql.ENUM("artist", "composer", "arranger", name="song_credit_role", create_type=False)

class Anime(Base):
    __tablename__ = "anime"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid.uuid4
    )
    
    title_en: Mapped[str | None] = mapped_column(sa.Text)
    title_jp: Mapped[str | None] = mapped_column(sa.Text)
    title_romaji: Mapped[str | None] = mapped_column(sa.Text)
    season: Mapped[str | None] = mapped_column(sa.String(10))    # 'Spring' | 'Summer' | 'Fall' | 'Winter'
    year: Mapped[int | None] = mapped_column(sa.Integer)
    type: Mapped[str | None] = mapped_column(sa.String(10))
    cover_image_url: Mapped[str | None] = mapped_column(sa.Text)
    
    linked_ids: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb")
    
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False
    )
    song_links: Mapped[list["SongAnime"]] = relationship(
        "SongAnime",
        back_populates="anime",
        cascade="all, delete-orphan"
    )


# Stores artists/arrangers/composers
class People(Base):
    __tablename__ = "people"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    kind: Mapped[str] = mapped_column(  # 'person' | 'group'
        sa.String(10),
        nullable=False
    )
    
    __table_args__ = (sa.CheckConstraint("kind in ('person','group')", name="ck_people_kind"),)
    primary_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    
    alt_names: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text),
        default=list,
        server_default=sa.text("'{}'"),
        nullable=False,
    )
    
    anisongdb_id: Mapped[int | None] = mapped_column(
        sa.Integer, unique=True, index=True, nullable=True
    )
    
    image_url: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    
    external_links: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(),
        onupdate=sa.func.now(), nullable=False
    )

    # Derived, via a membership join table
    members: Mapped[list["People"]] = relationship(
        "People",
        secondary="people_membership",
        primaryjoin="People.id == PeopleMembership.group_id",
        secondaryjoin="People.id == PeopleMembership.member_id",
        back_populates="member_of",
        viewonly=False,
        overlaps="member_of,members",
    )
    
    member_of: Mapped[list["People"]] = relationship(
        "People",
        secondary="people_membership",
        primaryjoin="People.id == PeopleMembership.member_id",
        secondaryjoin="People.id == PeopleMembership.group_id",
        back_populates="members",
        viewonly=False,
        overlaps="member_of,members",
    )


# Handles groups
class PeopleMembership(Base):
    __tablename__ = "people_membership"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True,
    ) 
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Song(Base):
    __tablename__ = "song"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    amq_song_id: Mapped[int | None] = mapped_column(
        sa.Integer, unique=True, index=True, nullable=True
    )

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)

    credits: Mapped[list["SongArtist"]] = relationship(
        "SongArtist",
        back_populates="song",
        cascade="all, delete-orphan"
    )
    
    audio: Mapped[str] = mapped_column(sa.Text, nullable=False)
    
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False
    )

    anime_links: Mapped[list["SongAnime"]] = relationship(
        "SongAnime",
        back_populates="song",
        cascade="all, delete-orphan"
    )


class SongArtist(Base):
    __tablename__ = "song_artist"
    
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("song.id", ondelete="CASCADE"),
        primary_key=True
    )
    people_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    role: Mapped[str] = mapped_column(song_credit_role, primary_key=True)
    song = relationship("Song", back_populates="credits")
    people = relationship("People")


# Song<->Anime junction with per-appearance metadata
class SongAnime(Base):
    __tablename__ = "song_anime"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("song.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    anime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("anime.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    is_dub: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false")
    )
    is_rebroadcast: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false")
    )

    # Per-appearance attributes
    use_type: Mapped[str] = mapped_column(song_type, nullable=False)  # OP | ED | IN
    sequence: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)  # e.g., OP1 -> 1, ED2 -> 2
    notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Practical de-duplication (allows multiple sequences for a given type)
    __table_args__ = (
        UniqueConstraint("song_id", "anime_id", "use_type", "sequence", name="uq_song_anime_usage"),
        Index("ix_song_anime_anime_song", "anime_id", "song_id"),
    )

    song: Mapped["Song"] = relationship("Song", back_populates="anime_links")
    anime: Mapped["Anime"] = relationship("Anime", back_populates="song_links")
