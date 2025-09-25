"""people + song_artist + membership

Revision ID: 0004
Revises: 0003
Create Date: 2025-09-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Ensure the enum exists (harmless if 0001 already created it)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'song_credit_role') THEN
        CREATE TYPE song_credit_role AS ENUM ('artist','composer','arranger');
      END IF;
    END$$;
    """)

    # Reference existing enum (do not create again)
    role_enum = postgresql.ENUM(name='song_credit_role', create_type=False)

    # people
    if not insp.has_table("people"):
        op.create_table(
            "people",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("kind", sa.String(10), nullable=False),
            sa.Column("primary_name", sa.Text(), nullable=False),
            sa.Column("alt_names", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("external_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                      server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("kind in ('person','group')", name="ck_people_kind"),
        )

    # people_membership (groups)
    if not insp.has_table("people_membership"):
        op.create_table(
            "people_membership",
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["people.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["member_id"], ["people.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("group_id", "member_id"),
        )

    # song_artist (use role_enum)
    if not insp.has_table("song_artist"):
        op.create_table(
            "song_artist",
            sa.Column("song_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("people_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", role_enum, nullable=False),
            sa.ForeignKeyConstraint(["song_id"], ["song.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["people_id"], ["people.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("song_id", "people_id", "role"),
        )

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("song_artist"):
        op.drop_table("song_artist")
    if insp.has_table("people_membership"):
        op.drop_table("people_membership")
    if insp.has_table("people"):
        op.drop_table("people")
    # keep enum in place for other revisions
