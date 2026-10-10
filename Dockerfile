FROM node:22-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY server /app/server
COPY --from=web /src/web/dist /app/web/dist
WORKDIR /app/server
RUN pip install --no-cache-dir .
ENV LAMATHEK_BIND_HOST=0.0.0.0
ENV PORT=5001
EXPOSE 5001
CMD ["sh", "-c", "alembic upgrade head && lamathek"]
