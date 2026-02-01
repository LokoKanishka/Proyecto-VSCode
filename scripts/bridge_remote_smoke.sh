#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
REMOTE_URL="${LUCY_WS_REMOTE_URL:-${LUCY_WS_BRIDGE_URLS:-ws://127.0.0.1:8766}}"
REMOTE_URL="${REMOTE_URL%%,*}"

if [ -z "$REMOTE_URL" ]; then
  echo "❌ LUCY_WS_REMOTE_URL vacío."
  exit 1
fi

echo "🌐 Remote bridge smoke hacia ${REMOTE_URL}"
"${PY_BIN}" - <<'PY'
import asyncio
import json
import os
import ssl
import sys
import time

import websockets

url = os.getenv("LUCY_WS_REMOTE_URL") or os.getenv("LUCY_WS_BRIDGE_URLS", "")
url = (url.split(",")[0] if url else "ws://127.0.0.1:8766").strip()
if not url:
    print("LUCY_WS_REMOTE_URL vacío", file=sys.stderr)
    sys.exit(1)

token = os.getenv("LUCY_WS_BRIDGE_TOKEN")
tls_ca = os.getenv("LUCY_WS_TLS_CA")

ssl_ctx = None
if url.startswith("wss://"):
    ssl_ctx = ssl.create_default_context()
    if tls_ca:
        ssl_ctx.load_verify_locations(cafile=tls_ca)

async def main() -> None:
    async with websockets.connect(url, ssl=ssl_ctx) as ws:
        subscribe = {"action": "subscribe", "topics": ["broadcast"]}
        if token:
            subscribe["token"] = token
        await ws.send(json.dumps(subscribe))
        await ws.recv()

        message = {
            "sender": "remote_smoke",
            "receiver": "broadcast",
            "type": "event",
            "content": "remote_smoke_ping",
            "data": {"ts": time.time()},
        }
        publish = {"action": "publish", "message": message}
        if token:
            publish["token"] = token
        await ws.send(json.dumps(publish))
        await ws.recv()

        deadline = time.time() + 6
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            payload = json.loads(raw)
            if payload.get("type") != "event":
                continue
            msg = payload.get("message") or {}
            if msg.get("content") == "remote_smoke_ping":
                print("OK: evento recibido")
                return
        raise RuntimeError("No llegó evento remote_smoke_ping")

try:
    asyncio.run(main())
except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)
PY

echo "✅ Remote smoke OK"
