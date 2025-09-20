from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("time_format", sa.String(), nullable=True),
    )
    op.create_table(
        "external_links",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), primary_key=True),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=True),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("expires_at", sa.String(), nullable=True),
    )

def downgrade():
    op.drop_table("external_links")
    op.drop_table("user_preferences")
    op.drop_table("users")