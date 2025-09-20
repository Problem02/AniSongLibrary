FROM python:3.12-slim
WORKDIR /app
ARG SERVICE_DIR

# System deps (add bash here)
RUN apt-get update && apt-get install -y bash build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps
COPY ${SERVICE_DIR}/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY ${SERVICE_DIR}/app ./app
COPY ${SERVICE_DIR}/alembic.ini ./alembic.ini
COPY ${SERVICE_DIR}/alembic ./alembic

# Start helper
RUN printf '#!/usr/bin/env bash\nset -e\n/scripts/wait-for-db.sh\nalembic upgrade head\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh \
    && chmod +x /app/start.sh

# wait script (requires build context at repo root)
COPY scripts/wait-for-db.sh /scripts/wait-for-db.sh
RUN chmod +x /scripts/wait-for-db.sh \
    && printf '#!/usr/bin/env bash\nset -e\n/scripts/wait-for-db.sh\nalembic upgrade head\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh \
    && chmod +x /app/start.sh

EXPOSE 8000
