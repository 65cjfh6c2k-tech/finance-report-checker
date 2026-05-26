#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

stop_servers() {
  echo
  echo "Stopping Finance Report Checker servers..."

  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi

  wait 2>/dev/null || true
}

require_path() {
  local path="$1"
  local message="$2"

  if [[ ! -e "${path}" ]]; then
    echo "Error: ${message}"
    exit 1
  fi
}

trap stop_servers EXIT INT TERM

require_path "${ROOT_DIR}/.venv" "Missing .venv directory."
require_path "${ROOT_DIR}/app.py" "Missing app.py."
require_path "${ROOT_DIR}/frontend/index.html" "Missing frontend/index.html."

echo "Starting Finance Report Checker..."

cd "${ROOT_DIR}"
".venv/bin/uvicorn" app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cd "${ROOT_DIR}/frontend"
python -m http.server 3000 --bind 127.0.0.1 &
FRONTEND_PID=$!

echo
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:3000"
echo
echo "Press Ctrl+C to stop both servers."

wait
