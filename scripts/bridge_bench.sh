#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
HOST="${LUCY_WS_HOST:-127.0.0.1}"
PORT="${LUCY_WS_PORT:-8766}"
BRIDGE_URL="ws://${HOST}:${PORT}"
COUNT="${BRIDGE_BENCH_COUNT:-200}"

echo "🚀 Bridge bench: gateway en ${BRIDGE_URL} (count=${COUNT})"
LUCY_WS_GATEWAY=1 LUCY_SWARM_CONSOLE=0 LUCY_WS_PORT="${PORT}" "${PY_BIN}" -m src.engine.swarm_runner &
GW_PID=$!

cleanup() {
  if ps -p "${GW_PID}" >/dev/null 2>&1; then
    kill "${GW_PID}"
    wait "${GW_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

sleep 2

"${PY_BIN}" - <<'PY'
import asyncio
import json
import os
import time
import websockets

async def main():
    host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
    port = os.getenv("LUCY_WS_PORT", "8766")
    count = int(os.getenv("BRIDGE_BENCH_COUNT", "200"))
    token = os.getenv("LUCY_WS_BRIDGE_TOKEN")
    url = f"ws://{host}:{port}"
    start = time.time()
    async with websockets.connect(url) as ws:
        for i in range(count):
            payload = {
                "sender": "bridge_bench",
                "receiver": "broadcast",
                "type": "event",
                "content": "bridge_bench_ping",
                "data": {"seq": i},
            }
            if token:
                payload["token"] = token
            await ws.send(json.dumps(payload))
            await ws.recv()
    elapsed = time.time() - start
    rate = count / elapsed if elapsed > 0 else 0
    print(f"✅ Bridge bench: {count} events in {elapsed:.2f}s ({rate:.1f}/s)")

asyncio.run(main())
PY
