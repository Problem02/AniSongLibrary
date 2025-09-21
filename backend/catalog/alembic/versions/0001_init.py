from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- Enums ---
    op.execute("CREATE TYPE song_type AS ENUM ('OP','ED','IN')")
    op.execute("CREATE TYPE song_credit_role AS ENUM ('artist','composer','arranger')")

    # --- anime ---
    op.create_table(
        "anime",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title_en", sa.Text(), nullable=True),
        sa.Column("title_jp", sa.Text(), nullable=True),
        sa.Column("title_romaji", sa.Text(), nullable=True),
        sa.Column("season", sa.String(length=10), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=True),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("linked_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- people ---
    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("primary_name", sa.Text(), nullable=False),
        sa.Column("alt_names", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("external_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind in ('person','group')", name="ck_people_kind"),
    )

    # --- people_membership (self-join helper for groups) ---
    op.create_table(
        "people_membership",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_people_membership_group", "people_membership", ["group_id"])
    op.create_index("ix_people_membership_member", "people_membership", ["member_id"])

    # --- song ---
    op.create_table(
        "song",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("anime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("anime.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Enum(name="song_type", create_type=False), nullable=False),
        sa.Column("is_dub", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_rebroadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("audio", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_song_anime_type", "song", ["anime_id", "type"])
    op.create_index("ix_song_updated_at", "song", ["updated_at"])

    # --- song_artist (association with role) ---
    op.create_table(
        "song_artist",
        sa.Column("song_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("song.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("people_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Enum(name="song_credit_role", create_type=False), primary_key=True),
    )
    op.create_index("ix_song_artist_people_role", "song_artist", ["people_id", "role"])
    op.create_index("ix_song_artist_song_role", "song_artist", ["song_id", "role"])


def downgrade():
    # drop in reverse order of dependencies / indexes first
    op.drop_index("ix_song_artist_song_role", table_name="song_artist")
    op.drop_index("ix_song_artist_people_role", table_name="song_artist")
    op.drop_table("song_artist")

    op.drop_index("ix_song_updated_at", table_name="song")
    op.drop_index("ix_song_anime_type", table_name="song")
    op.drop_table("song")

    op.drop_index("ix_people_membership_member", table_name="people_membership")
    op.drop_index("ix_people_membership_group", table_name="people_membership")
    op.drop_table("people_membership")

    op.drop_table("people")

    op.drop_table("anime")

    # finally drop enum types
    op.execute("DROP TYPE song_credit_role")
    op.execute("DROP TYPE song_type")
