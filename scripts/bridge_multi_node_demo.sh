#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
HOST="${LUCY_WS_HOST:-127.0.0.1}"
PORT="${LUCY_WS_PORT:-8766}"
BRIDGE_URL="ws://${HOST}:${PORT}"

echo "🚀 Nodo A (gateway) en ${BRIDGE_URL}"
LUCY_WS_GATEWAY=1 LUCY_SWARM_CONSOLE=0 LUCY_WS_PORT="${PORT}" "${PY_BIN}" -m src.engine.swarm_runner &
GW_PID=$!

cleanup() {
  for pid in "${BRIDGE_PID:-}" "${GW_PID:-}"; do
    if [ -n "${pid}" ] && ps -p "${pid}" >/dev/null 2>&1; then
      kill "${pid}"
      wait "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

sleep 2

echo "🔗 Nodo B (bridge) conectado a ${BRIDGE_URL}"
LUCY_WS_BRIDGE_URL="${BRIDGE_URL}" LUCY_WS_BRIDGE_TOPICS="broadcast,final_response" LUCY_SWARM_CONSOLE=0 "${PY_BIN}" -m src.engine.swarm_runner &
BRIDGE_PID=$!

sleep 2

echo "🧪 Publicando evento a través del gateway..."
"${PY_BIN}" - <<'PY'
import asyncio
import json
import os
import websockets

async def main():
    host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
    port = os.getenv("LUCY_WS_PORT", "8766")
    url = f"ws://{host}:{port}"
    async with websockets.connect(url) as ws:
        payload = {
            "sender": "bridge_demo",
            "receiver": "broadcast",
            "type": "event",
            "content": "bridge_demo_ping",
            "data": {"hello": "bridge"},
        }
        await ws.send(json.dumps(payload))
        await ws.recv()

asyncio.run(main())
PY

echo "✅ Demo lista. Revisá logs de ambos nodos para ver bridge_stats."
