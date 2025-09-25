from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

# ---- ENUM definitions ----
# Objects used to CREATE/DROP the underlying PG enum types:
song_type_create = postgresql.ENUM("OP", "ED", "IN", name="song_type")
song_credit_role_create = postgresql.ENUM("artist", "composer", "arranger", name="song_credit_role")

# Reference-only enums used on columns (never attempt to CREATE):
song_type = postgresql.ENUM(name="song_type", create_type=False)
song_credit_role = postgresql.ENUM(name="song_credit_role", create_type=False)

def upgrade():
    bind = op.get_bind()

    # Create enum types once (no-op if they already exist)
    song_type_create.create(bind, checkfirst=True)
    song_credit_role_create.create(bind, checkfirst=True)

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

    # --- people_membership ---
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
        sa.Column("type", song_type, nullable=False),  # reference-only enum
        sa.Column("is_dub", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_rebroadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("audio", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_song_anime_type", "song", ["anime_id", "type"])
    op.create_index("ix_song_updated_at", "song", ["updated_at"])

    # --- song_artist ---
    op.create_table(
        "song_artist",
        sa.Column("song_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("song.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("people_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", song_credit_role, primary_key=True),  # reference-only enum
    )
    op.create_index("ix_song_artist_people_role", "song_artist", ["people_id", "role"])
    op.create_index("ix_song_artist_song_role", "song_artist", ["song_id", "role"])

def downgrade():
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

    bind = op.get_bind()
    song_credit_role_create.drop(bind, checkfirst=True)
    song_type_create.drop(bind, checkfirst=True)
