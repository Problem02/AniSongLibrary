"""song extras (audio, flags, timestamps)

Revision ID: 0003
Revises: 0002
Create Date: 2025-09-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("song")}

    if "is_dub" not in cols:
        op.add_column("song", sa.Column("is_dub", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if "is_rebroadcast" not in cols:
        op.add_column("song", sa.Column("is_rebroadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if "audio" not in cols:
        # add with default so existing rows pass NOT NULL, then drop the default
        op.add_column("song", sa.Column("audio", sa.Text(), nullable=False, server_default=""))
        op.execute("ALTER TABLE song ALTER COLUMN audio DROP DEFAULT")

    if "created_at" not in cols:
        op.add_column(
            "song",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if "updated_at" not in cols:
        op.add_column(
            "song",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

def downgrade() -> None:
    # safe drops if present
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("song")}
    if "updated_at" in cols:
        op.drop_column("song", "updated_at")
    if "created_at" in cols:
        op.drop_column("song", "created_at")
    if "audio" in cols:
        op.drop_column("song", "audio")
    if "is_rebroadcast" in cols:
        op.drop_column("song", "is_rebroadcast")
    if "is_dub" in cols:
        op.drop_column("song", "is_dub")
