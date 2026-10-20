#!/usr/bin/env bash
# End-to-end stack: fresh database with the demo seed, the built client served by
# Flask under gunicorn (like production), mails to the local SMTP sink, every API
# answer checked against its model. Started by playwright.config.ts.
set -euo pipefail

WEB="$(cd "$(dirname "$0")/../.." && pwd)"
REPO="$(cd "$WEB/.." && pwd)"
PORT="${E2E_PORT:-5199}"
STATE="$(mktemp -d -t lamathek-e2e)"
trap 'rm -rf "$STATE"' EXIT

PYTHON="$REPO/server/.venv/bin/python"
GUNICORN="$REPO/server/.venv/bin/gunicorn"
[ -x "$PYTHON" ] || PYTHON=python3
[ -x "$GUNICORN" ] || GUNICORN=gunicorn

# Never read a developer's .env/.env.local (real SMTP credentials, database path).
export LAMATHEK_SKIP_DOTENV=1
export SQLITE_PATH="$STATE/lamathek.sqlite3"
export MEDIA_PATH="$STATE/media"
export LAMATHEK_STATIC_ROOT="$STATE/dist"
export SECRET_KEY="e2e-$(date +%s)-$RANDOM"
export FRONTEND_URL="http://127.0.0.1:$PORT"
export AUTH_DEV_BYPASS=1
export AUTH_DEV_BYPASS_ALLOW=1
export AUTH_DEV_SUB="e2e:admin"
export AUTH_DEV_NAME="Erika Admin"
export AUTH_DEV_EMAIL="erika@example.org"
export SMTP_HOST=127.0.0.1
export SMTP_PORT="${E2E_SMTP_PORT:-2525}"
export SMTP_STARTTLS=0
export SMTP_FROM="lamathek@example.org"
export API_CONTRACT_CHECK=1

(cd "$WEB" && npx vite build --outDir "$LAMATHEK_STATIC_ROOT" --emptyOutDir --logLevel warn)
"$PYTHON" "$REPO/scripts/seed_demo.py" --reset >/dev/null

cd "$REPO/server"
"$GUNICORN" -w 1 --threads 8 -b "127.0.0.1:$PORT" --access-logfile - 'lamathek.app:create_app()' &
trap 'kill $! 2>/dev/null; rm -rf "$STATE"' EXIT
wait
