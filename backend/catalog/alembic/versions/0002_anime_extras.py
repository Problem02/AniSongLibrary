"""anime extras (linked_ids, romaji, type, updated_at)

Revision ID: 0002
Revises: b969788927ea
Create Date: 2025-09-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "b969788927ea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("anime")}

    # Add missing columns (idempotent: only if not already present)
    if "title_romaji" not in cols:
        op.add_column("anime", sa.Column("title_romaji", sa.Text(), nullable=True))

    if "type" not in cols:
        op.add_column("anime", sa.Column("type", sa.String(length=10), nullable=True))

    if "linked_ids" not in cols:
        op.add_column(
            "anime",
            sa.Column(
                "linked_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )

    if "updated_at" not in cols:
        op.add_column(
            "anime",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    # GIN index for jsonb containment lookups on linked_ids
    op.execute("CREATE INDEX IF NOT EXISTS ix_anime_linked_ids_gin ON anime USING gin (linked_ids)")


def downgrade() -> None:
    # Drop index first
    op.execute("DROP INDEX IF EXISTS ix_anime_linked_ids_gin")

    # Drop columns if they exist (safe on multiple envs)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("anime")}

    if "updated_at" in cols:
        op.drop_column("anime", "updated_at")
    if "linked_ids" in cols:
        op.drop_column("anime", "linked_ids")
    if "type" in cols:
        op.drop_column("anime", "type")
    if "title_romaji" in cols:
        op.drop_column("anime", "title_romaji")
