from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    DO $$
    BEGIN
      -- rename if old column exists
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='people' AND column_name='anisongdb_artist_id'
      ) THEN
        ALTER TABLE people RENAME COLUMN anisongdb_artist_id TO anisongdb_id;
      ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='people' AND column_name='anisongdb_id'
      ) THEN
        ALTER TABLE people ADD COLUMN anisongdb_id integer;
      END IF;

      -- drop old unique constraint name if present
      IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='people' AND constraint_name='uq_people_anisongdb_artist_id'
      ) THEN
        ALTER TABLE people DROP CONSTRAINT uq_people_anisongdb_artist_id;
      END IF;

      -- ensure new unique constraint exists
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='people' AND constraint_name='uq_people_anisongdb_id'
      ) THEN
        ALTER TABLE people ADD CONSTRAINT uq_people_anisongdb_id UNIQUE (anisongdb_id);
      END IF;
    END $$;
    """)

def downgrade():
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='people' AND constraint_name='uq_people_anisongdb_id'
      ) THEN
        ALTER TABLE people DROP CONSTRAINT uq_people_anisongdb_id;
      END IF;

      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='people' AND column_name='anisongdb_id'
      ) THEN
        ALTER TABLE people RENAME COLUMN anisongdb_id TO anisongdb_artist_id;
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='people' AND constraint_name='uq_people_anisongdb_artist_id'
      ) THEN
        ALTER TABLE people ADD CONSTRAINT uq_people_anisongdb_artist_id UNIQUE (anisongdb_artist_id);
      END IF;
    END $$;
    """)
