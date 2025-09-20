from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "anime",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title_en", sa.String()),
        sa.Column("title_jp", sa.String()),
        sa.Column("season", sa.String()),
        sa.Column("year", sa.Integer()),
        sa.Column("cover_image_url", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "artist",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_table(
        "song",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("anime_id", sa.String(), sa.ForeignKey("anime.id"), nullable=False),
    )
    op.create_table(
        "song_artists",
        sa.Column("song_id", sa.String(), sa.ForeignKey("song.id"), primary_key=True),
        sa.Column("artist_id", sa.String(), sa.ForeignKey("artist.id"), primary_key=True),
        sa.Column("role", sa.String()),
    )
    op.create_table(
        "external_links",
        sa.Column("entity_type", sa.String(), primary_key=True),
        sa.Column("entity_id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), primary_key=True),
        sa.Column("provider_id", sa.String(), nullable=False),
    )

def downgrade():
    op.drop_table("external_links")
    op.drop_table("song_artists")
    op.drop_table("song")
    op.drop_table("artist")
    op.drop_table("anime")