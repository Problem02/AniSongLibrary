"""m2m Song<->Anime (move type to link)

Revision ID: b969788927ea
Revises: 0001_init
Create Date: 2025-09-21 20:53:40.559481
"""

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b969788927ea'
down_revision = '0001_init'
branch_labels = None
depends_on = None

# Reference the existing enum; do NOT recreate it here
song_type = postgresql.ENUM(name="song_type", create_type=False)

def _drop_child_fks(conn, parent_table: str):
    # Drop all foreign keys that reference parent_table (e.g., "song" or "anime")
    rows = conn.execute(sa.text("""
        SELECT conname AS fk_name,
               conrelid::regclass::text AS table_name
        FROM pg_constraint c
        JOIN pg_class r ON c.confrelid = r.oid
        WHERE c.contype = 'f' AND r.relname = :parent
    """), {"parent": parent_table}).fetchall()
    for fk_name, table_name in rows:
        op.drop_constraint(fk_name, table_name, type_="foreignkey")

def upgrade():
    conn = op.get_bind()

    # 0) Drop FKs referencing parent PKs we're about to convert to UUID
    _drop_child_fks(conn, "song")
    _drop_child_fks(conn, "anime")

    # 1) Convert parent PKs to UUID (only if not already UUID)
    atype = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name='anime' AND column_name='id'
    """)).scalar()
    if atype and atype.lower() != "uuid":
        op.execute("ALTER TABLE anime ALTER COLUMN id TYPE uuid USING id::uuid")

    stype = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name='song' AND column_name='id'
    """)).scalar()
    if stype and stype.lower() != "uuid":
        op.execute("ALTER TABLE song ALTER COLUMN id TYPE uuid USING id::uuid")
        
    # 2) Create the junction table AFTER ids are UUID
    op.create_table(
        "song_anime",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("song_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("song.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anime_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("anime.id", ondelete="CASCADE"), nullable=False),
        sa.Column("use_type", song_type, nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("song_id", "anime_id", "use_type", "sequence", name="uq_song_anime_usage"),
    )
    op.create_index("ix_song_anime_anime_id", "song_anime", ["anime_id"])
    op.create_index("ix_song_anime_song_id", "song_anime", ["song_id"])
    op.create_index("ix_song_anime_anime_song", "song_anime", ["anime_id", "song_id"])

    # 3) Backfill from legacy columns (song.anime_id + song.type) BEFORE dropping them
    insp = sa.inspect(conn)
    song_cols = {c["name"] for c in insp.get_columns("song")}
    if "anime_id" in song_cols and "type" in song_cols:
        rows = conn.execute(sa.text("""
            SELECT id AS song_id, anime_id, type AS use_type
            FROM song
            WHERE anime_id IS NOT NULL
        """)).fetchall()
        if rows:
            insert_stmt = sa.text("""
                INSERT INTO song_anime (id, song_id, anime_id, use_type)
                VALUES (:id, :song_id::uuid, :anime_id::uuid, :use_type)
                ON CONFLICT DO NOTHING
            """)
            for r in rows:
                conn.execute(insert_stmt, {
                    "id": str(uuid.uuid4()),
                    "song_id": str(r.song_id),
                    "anime_id": str(r.anime_id),
                    "use_type": r.use_type,
                })

    # 4) Now drop the legacy columns
    if "anime_id" in song_cols or "type" in song_cols:
        with op.batch_alter_table("song") as batch:
            if "anime_id" in song_cols:
                batch.drop_column("anime_id")
            if "type" in song_cols:
                batch.drop_column("type")

def downgrade():
    # Recreate columns on song (nullable to avoid data loss on multi-links)
    with op.batch_alter_table("song") as batch:
        batch.add_column(sa.Column("anime_id", postgresql.UUID(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("type", song_type, nullable=True))
        batch.create_foreign_key("fk_song_anime_id_anime", "anime", ["anime_id"], ["id"], ondelete="CASCADE")

    # Best-effort: for each song, pick an arbitrary (min) linked anime/use_type
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE song s SET
            anime_id = sa1.anime_id,
            type = sa1.use_type
        FROM (
            SELECT song_id, MIN(anime_id) AS anime_id, MIN(use_type) AS use_type
            FROM song_anime
            GROUP BY song_id
        ) sa1
        WHERE s.id = sa1.song_id
    """))

    op.drop_index("ix_song_anime_anime_song", table_name="song_anime")
    op.drop_constraint("uq_song_anime_usage", "song_anime", type_="unique")
    op.drop_table("song_anime")
