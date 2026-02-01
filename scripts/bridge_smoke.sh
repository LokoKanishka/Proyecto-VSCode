#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
HOST="${LUCY_WS_HOST:-127.0.0.1}"
PORT="${LUCY_WS_PORT:-8766}"
BRIDGE_URL="ws://${HOST}:${PORT}"

echo "🚀 Bridge smoke: iniciando gateway en ${BRIDGE_URL}"
LUCY_WS_GATEWAY=1 LUCY_WS_PORT="${PORT}" LUCY_SWARM_CONSOLE=0 "${PY_BIN}" -m src.engine.swarm_runner &
GW_PID=$!

cleanup() {
  if ps -p "${GW_PID}" >/dev/null 2>&1; then
    kill "${GW_PID}"
    wait "${GW_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

sleep 2

echo "🧪 Publicando evento por WS..."
"${PY_BIN}" - <<'PY'
import asyncio
import json
import os
import websockets

async def main():
    host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
    port = os.getenv("LUCY_WS_PORT", "8766")
    token = os.getenv("LUCY_WS_BRIDGE_TOKEN")
    url = f"ws://{host}:{port}"
    async with websockets.connect(url) as ws:
        payload = {
            "sender": "bridge_smoke",
            "receiver": "broadcast",
            "type": "event",
            "content": "bridge_smoke_ping",
            "data": {"hello": "world"},
        }
        if token:
            payload["token"] = token
        await ws.send(json.dumps(payload))
        await ws.recv()

asyncio.run(main())
PY

echo "✅ Bridge smoke listo (gateway respondió)."
