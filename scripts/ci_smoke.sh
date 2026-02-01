#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"

echo "🧪 CI smoke: tests clave"
"${PY_BIN}" -m pytest tests/test_memory_manager.py tests/test_web_api.py tests/test_swarm_e2e_pipeline.py

echo "🧪 CI smoke: memory snapshot"
"${PY_BIN}" ./scripts/memory_snapshot_smoke.py

echo "✅ CI smoke OK"
