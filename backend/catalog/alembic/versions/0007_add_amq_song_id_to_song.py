from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_amq_song_id_to_song"
down_revision = "0006"
branch_labels = None
depends_on = None

def upgrade():
    # Add nullable column (safe for existing rows)
    op.add_column("song", sa.Column("amq_song_id", sa.Integer(), nullable=True))
    # Unique index allows multiple NULLs in Postgres, so no data migration needed
    op.create_index("ix_song_amq_song_id", "song", ["amq_song_id"], unique=True)

def downgrade():
    op.drop_index("ix_song_amq_song_id", table_name="song")
    op.drop_column("song", "amq_song_id")
