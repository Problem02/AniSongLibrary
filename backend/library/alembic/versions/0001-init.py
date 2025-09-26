from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None

def upgrade():
    op.create_table(
        "library_entry",
        sa.Column("user_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("song_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("amq_song_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_library_entry_score"),
    )
    op.create_index("ix_library_user_updated", "library_entry", ["user_id"], postgresql_using=None)
    op.create_index("ix_library_user_score", "library_entry", ["user_id", "score"], postgresql_using=None)
    op.create_index("ix_library_amq", "library_entry", ["amq_song_id"], postgresql_using=None)

def downgrade():
    op.drop_index("ix_library_amq", table_name="library_entry")
    op.drop_index("ix_library_user_score", table_name="library_entry")
    op.drop_index("ix_library_user_updated", table_name="library_entry")
    op.drop_table("library_entry")
