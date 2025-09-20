import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# --- Ensure /app is on sys.path so "import app.***" always works ---
here = os.path.dirname(__file__)              # /app/alembic
repo_root = os.path.abspath(os.path.join(here, ".."))  # /app
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

config = context.config

# Wire DATABASE_URL from env -> alembic.ini
section = config.config_ini_section
config.set_section_option(section, "DATABASE_URL", os.environ.get("DATABASE_URL", ""))

# Logging (optional)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models *after* sys.path fix
from app.db.models import Base  # noqa: E402

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
