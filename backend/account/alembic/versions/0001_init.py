from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1) Extensions (safe if already present)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # 2) Enum type (model uses create_type=False)
    op.execute("CREATE TYPE user_role AS ENUM ('ADMIN', 'USER');")

    # 3) users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("role", postgresql.ENUM(name="user_role", create_type=False), nullable=False, server_default="USER"),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Index for searching by recent users
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

def downgrade():
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role;")
    # (leave citext installed)
