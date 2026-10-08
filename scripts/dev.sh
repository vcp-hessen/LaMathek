#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "${ROOT}/.env.dev" ]]; then
  echo "Missing ${ROOT}/.env.dev" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${ROOT}/.env.dev"
set +a

export LAMATHEK_ENV=dev
LAMATHEK_API_PORT="${LAMATHEK_API_PORT:-5001}"
WEB_PORT="${WEB_PORT:-5173}"
export LAMATHEK_API_PORT

API_PID=""
WEB_PID=""

stop_listen_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "Stopping previous listener on port ${port} (${pids}) …"
    # shellcheck disable=SC2086
    kill ${pids} 2>/dev/null || true
    sleep 0.5
  fi
}

cleanup() {
  if [[ -n "${WEB_PID}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ ! -d "${ROOT}/server/.venv" ]]; then
  echo "Creating Python venv in server/.venv …"
  python3 -m venv "${ROOT}/server/.venv"
fi

# shellcheck source=/dev/null
source "${ROOT}/server/.venv/bin/activate"
pip install -q -e "${ROOT}/server[dev]"

if [[ ! -d "${ROOT}/web/node_modules" ]]; then
  echo "Installing web dependencies …"
  npm install --prefix "${ROOT}/web"
fi

echo "Running database migrations …"
(cd "${ROOT}/server" && alembic upgrade head)

stop_listen_port "${LAMATHEK_API_PORT}"
stop_listen_port "${WEB_PORT}"

API_URL="http://127.0.0.1:${LAMATHEK_API_PORT}"
WEB_URL="http://127.0.0.1:${WEB_PORT}"

echo "Starting API on ${API_URL} …"
(cd "${ROOT}/server" && lamathek) &
API_PID=$!

for _ in $(seq 1 40); do
  if curl -sf "${API_URL}/api/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "API exited before becoming healthy. Check the log above." >&2
    exit 1
  fi
  sleep 0.25
done

if ! curl -sf "${API_URL}/api/health" >/dev/null 2>&1; then
  echo "API did not respond on ${API_URL}/api/health" >&2
  exit 1
fi

echo "Starting web on ${WEB_URL} …"
LAMATHEK_API_PORT="${LAMATHEK_API_PORT}" npm run dev --prefix "${ROOT}/web" -- --host 127.0.0.1 --port "${WEB_PORT}" &
WEB_PID=$!

cat <<EOF

LaMathek dev stack is running.
  UI:  ${WEB_URL}
  API: ${API_URL}

Sign in with "Anmelden" (dev bypass, no OIDC).
Press Ctrl+C to stop both servers.

EOF

wait "${WEB_PID}"
