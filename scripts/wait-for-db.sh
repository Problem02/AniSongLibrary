#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL}"

echo "Waiting for DB: $DB_URL"
until python - <<'PY'
import os, time
import psycopg
url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')
for _ in range(60):
    try:
        with psycopg.connect(url, connect_timeout=2):
            print('DB ready')
            raise SystemExit(0)
    except Exception as e:
        time.sleep(1)
raise SystemExit(1)
PY
    do sleep 1; done