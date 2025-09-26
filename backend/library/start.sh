#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:?DATABASE_URL not set}"

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000