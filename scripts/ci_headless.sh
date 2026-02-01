#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export LUCY_NO_EMB=1
export LUCY_FAISS_ALWAYS_ON=0
export LUCY_BROWSER_AUTO_FALLBACK=0
export LUCY_SWARM_CONSOLE=0

PY_BIN="${PY_BIN:-python3}"

echo "🧪 CI headless: tests clave"
"${PY_BIN}" -m pytest tests/test_swarm_e2e_pipeline.py tests/test_ws_bridge_multi.py -q

echo "✅ CI headless OK"
