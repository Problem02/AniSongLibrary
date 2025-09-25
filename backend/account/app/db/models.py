import uuid
import sqlalchemy as sa
from sqlalchemy import UUID
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects import postgresql

Base = declarative_base()

# Reference existing pg enums created by Alembic; do NOT auto-create types here
user_role = postgresql.ENUM("ADMIN", "USER", name="user_role", create_type=False)

# Used for case insensitive unique emails
CITEXT = postgresql.CITEXT

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid.uuid4
    )
    
    role: Mapped[str] = mapped_column(user_role, nullable=False, server_default="USER")
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    display_name: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False
    )
    last_login_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True
    )
