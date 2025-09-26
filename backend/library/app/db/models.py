# app/models.py
import uuid
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()

class LibraryEntry(Base):
    __tablename__ = "library_entry"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    song_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)

    amq_song_id: Mapped[int | None] = mapped_column(sa.Integer)

    score: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)  # 0..100
    is_favorite: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    note: Mapped[str | None] = mapped_column(sa.Text)

    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_library_entry_score"),
        sa.Index("ix_library_user_updated", "user_id", sa.text("updated_at DESC")),
        sa.Index("ix_library_user_score", "user_id", "score", sa.text("updated_at DESC")),
        sa.Index("ix_library_amq", "amq_song_id"),
    )
