#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
HOST="${LUCY_WS_HOST:-127.0.0.1}"
PORT="${LUCY_WS_PORT:-8777}"
TOKEN="${LUCY_WS_BRIDGE_TOKEN:-demo-token}"

TMP_DIR="/tmp/lucy_ws_tls"
CERT="${TMP_DIR}/cert.pem"
KEY="${TMP_DIR}/key.pem"

mkdir -p "${TMP_DIR}"
if ! command -v openssl >/dev/null 2>&1; then
  echo "❌ openssl no disponible"
  exit 1
fi

if [ ! -f "${CERT}" ] || [ ! -f "${KEY}" ]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "${KEY}" -out "${CERT}" -days 1 \
    -subj "/CN=lucy-bridge"
fi

BRIDGE_URL="wss://${HOST}:${PORT}"

echo "🚀 Gateway TLS en ${BRIDGE_URL}"
LUCY_WS_GATEWAY=1 LUCY_WS_PORT="${PORT}" \
LUCY_WS_TLS_CERT="${CERT}" LUCY_WS_TLS_KEY="${KEY}" \
LUCY_WS_BRIDGE_TOKEN="${TOKEN}" \
LUCY_SWARM_CONSOLE=0 "${PY_BIN}" -m src.engine.swarm_runner &
GW_PID=$!

cleanup() {
  if ps -p "${GW_PID}" >/dev/null 2>&1; then
    kill "${GW_PID}"
    wait "${GW_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

sleep 2

echo "🔗 Bridge TLS conectado"
LUCY_WS_BRIDGE_URLS="${BRIDGE_URL}" \
LUCY_WS_TLS_CA="${CERT}" \
LUCY_WS_BRIDGE_TOKEN="${TOKEN}" \
LUCY_SWARM_CONSOLE=0 "${PY_BIN}" -m src.engine.swarm_runner &
BRIDGE_PID=$!

sleep 2

echo "🧪 Publicando evento por WSS..."
"${PY_BIN}" - <<'PY'
import asyncio
import json
import os
import ssl
import websockets

async def main():
    host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
    port = os.getenv("LUCY_WS_PORT", "8777")
    token = os.getenv("LUCY_WS_BRIDGE_TOKEN", "demo-token")
    ca = os.getenv("LUCY_WS_TLS_CA")
    url = f"wss://{host}:{port}"
    ctx = ssl.create_default_context(cafile=ca) if ca else ssl._create_unverified_context()
    async with websockets.connect(url, ssl=ctx) as ws:
        payload = {
            "sender": "tls_demo",
            "receiver": "broadcast",
            "type": "event",
            "content": "bridge_tls_demo",
            "data": {"tls": True},
            "token": token,
        }
        await ws.send(json.dumps(payload))
        await ws.recv()

asyncio.run(main())
PY

if ps -p "${BRIDGE_PID}" >/dev/null 2>&1; then
  kill "${BRIDGE_PID}"
  wait "${BRIDGE_PID}" 2>/dev/null || true
fi

echo "✅ TLS+token demo OK"
