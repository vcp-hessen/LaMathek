FROM node:22-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
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
WORKDIR /app/server
RUN pip install --no-cache-dir .
ENV LAMATHEK_BIND_HOST=0.0.0.0
ENV LAMATHEK_STATIC_ROOT=/app/web/dist
ENV SQLITE_PATH=/data/lamathek.sqlite3
ENV PORT=5001
EXPOSE 5001
CMD ["lamathek"]
