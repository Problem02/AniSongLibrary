import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

Base = declarative_base()

song_type = sa.Enum("OP", "ED", "IN", name="song_type")
song_credit_role = sa.Enum("artist", "composer", "arranger", name="song_credit_role")

class Anime(Base):
    __tablename__ = "anime"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid.uuid4)
    title_en: Mapped[str | None] = mapped_column(sa.Text)
    title_jp: Mapped[str | None] = mapped_column(sa.Text)
    title_romaji: Mapped[str | None] = mapped_column(sa.Text)
    season: Mapped[str | None] = mapped_column(sa.String(10))    # 'Spring' | 'Summer' | 'Fall' | 'Winter'
    year: Mapped[int | None] = mapped_column(sa.Integer)
    type: Mapped[str | None] = mapped_column(sa.String(10))
    cover_image_url: Mapped[str | None] = mapped_column(sa.Text)
    linked_ids: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=sa.text("'{}'::jsonb"))
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

# Stores artists/arrangers/composers
class People(Base):
    __tablename__ = "people"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(sa.String(10), nullable=False)  # 'person' | 'group'
    __table_args__ = (sa.CheckConstraint("kind in ('person','group')", name="ck_people_kind"),)
    primary_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    alt_names: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text),
        default=list,
        server_default=sa.text("'{}'"),
        nullable=False,
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
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anime_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("anime.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    type: Mapped[str] = mapped_column(song_type, nullable=False)  # 'OP' | 'ED' | 'IN'
    credits: Mapped[list["SongArtist"]] = relationship("SongArtist", back_populates="song", cascade="all, delete-orphan")
    is_dub: Mapped[bool] = mapped_column(sa.Boolean, nullable=False,server_default=sa.text("false"))
    is_rebroadcast: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    audio: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

class SongArtist(Base):
    __tablename__ = "song_artist"
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("song.id", ondelete="CASCADE"), primary_key=True)
    people_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(song_credit_role, primary_key=True)
    song   = relationship("Song",   back_populates="credits")
    people = relationship("People")
