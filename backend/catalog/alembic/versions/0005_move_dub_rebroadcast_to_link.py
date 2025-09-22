# alembic revision: move dub/rebroadcast to song_anime
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

def upgrade():
    # 1) add columns to link table (defaults to false, non-null)
    op.add_column("song_anime", sa.Column("is_dub", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("song_anime", sa.Column("is_rebroadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # 2) backfill from song table if those columns exist (works even if they don't)
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='song' AND column_name='is_dub'
      ) THEN
        UPDATE song_anime sa
        SET is_dub = s.is_dub,
            is_rebroadcast = s.is_rebroadcast
        FROM song s
        WHERE s.id = sa.song_id;
      END IF;
    END $$;
    """)

    # 3) drop columns from song table if they exist
    op.execute("ALTER TABLE song DROP COLUMN IF EXISTS is_dub;")
    op.execute("ALTER TABLE song DROP COLUMN IF EXISTS is_rebroadcast;")

def downgrade():
    # 1) add columns back on song (default false)
    op.add_column("song", sa.Column("is_dub", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("song", sa.Column("is_rebroadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # 2) approximate backfill: set true if ANY link is true
    op.execute("""
    UPDATE song s SET
      is_dub = EXISTS (SELECT 1 FROM song_anime sa WHERE sa.song_id = s.id AND sa.is_dub),
      is_rebroadcast = EXISTS (SELECT 1 FROM song_anime sa WHERE sa.song_id = s.id AND sa.is_rebroadcast);
    """)

    # 3) drop the link columns
    op.drop_column("song_anime", "is_rebroadcast")
    op.drop_column("song_anime", "is_dub")
