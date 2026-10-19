FROM node:22-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# Workflow gates are shared with the API and imported via the @shared alias.
COPY server/lamathek/domain /src/server/lamathek/domain
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY server /app/server
COPY --from=web /src/web/dist /app/web/dist
RUN pip install --no-cache-dir /app/server
WORKDIR /data
ENV LAMATHEK_STATIC_ROOT=/app/web/dist
ENV SQLITE_PATH=/data/lamathek.sqlite3
ENV PORT=5001
EXPOSE 5001
# One worker: SQLite has a single writer, and the mail outbox thread runs in-process.
CMD ["sh", "-c", "lamathek migrate && exec gunicorn --workers 1 --threads 8 --bind 0.0.0.0:${PORT} --access-logfile - 'lamathek.app:create_app()'"]
