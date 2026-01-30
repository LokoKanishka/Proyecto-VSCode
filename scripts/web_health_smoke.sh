#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HOST="${LUCY_WEB_HOST:-127.0.0.1}"
PORT="${LUCY_WEB_PORT:-5002}"

LOG="/tmp/lucy_web_smoke.log"

echo "Iniciando smoke test de la UI (host=$HOST, port=$PORT)..."
LUCY_WEB_ALLOW_UNSAFE=1 FLASK_DEBUG=0 LUCY_WEB_PORT="$PORT" LUCY_WEB_HOST="$HOST" \
  "$ROOT_DIR/.venv-lucy-voz/bin/python" "$ROOT_DIR/lucy_web/app.py" >"$LOG" 2>&1 &
PID=$!

trap 'echo "Deteniendo servidor..."; kill "$PID"; wait "$PID" 2>/dev/null || true' EXIT

sleep 4

curl -fs "http://$HOST:$PORT/api/health"

kill "$PID"
wait "$PID" 2>/dev/null || true
trap - EXIT

echo "Smoke test completado."
