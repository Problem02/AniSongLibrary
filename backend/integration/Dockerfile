FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN printf '#!/usr/bin/env bash\nset -e\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh && chmod +x /app/start.sh
EXPOSE 8000