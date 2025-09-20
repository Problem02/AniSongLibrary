FROM python:3.12-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Start helper
RUN printf '#!/usr/bin/env bash\nset -e\n/scripts/wait-for-db.sh\nalembic upgrade head\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh && \
    chmod +x /app/start.sh

# wait script
COPY ../../scripts/wait-for-db.sh /scripts/wait-for-db.sh
RUN chmod +x /scripts/wait-for-db.sh

EXPOSE 8000