# backend/integration/Dockerfile
FROM python:3.12-slim
WORKDIR /app
ARG SERVICE_DIR

RUN apt-get update && apt-get install -y bash curl && rm -rf /var/lib/apt/lists/*

# 1) requirements first, then install
COPY ${SERVICE_DIR}/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2) then your app code
COPY ${SERVICE_DIR}/app ./app

# 3) start
RUN printf '#!/usr/bin/env bash\nset -e\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh \
    && chmod +x /app/start.sh

EXPOSE 8000
