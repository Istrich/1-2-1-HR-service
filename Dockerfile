# HR 1-2-1 Web — данные снаружи через тома (см. docker-compose.yml).
# Статический ffmpeg без apt-get (сборка работает при ограниченном доступе к Debian mirrors).
FROM mwader/static-ffmpeg:7.1 AS ffmpeg

# --- Frontend Build Stage ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Final Python Stage ---
FROM python:3.11-slim-bookworm

COPY --from=ffmpeg /ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV XDG_CACHE_HOME=/data/cache
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
