from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "library_entries",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("entity_type", sa.String(), primary_key=True),
        sa.Column("entity_id", sa.String(), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "ratings",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("song_id", sa.String(), primary_key=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "rating_aggregates",
        sa.Column("anime_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("rated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_songs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Integer(), nullable=True),
        sa.Column("fully_rated", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

def downgrade():
    op.drop_table("rating_aggregates")
    op.drop_table("ratings")
    op.drop_table("library_entries")