#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MAX_LINES="${LUCY_LOG_MAX_LINES:-20000}"
LOGS=(
  "logs/bus_metrics.jsonl"
  "logs/bridge_metrics.jsonl"
  "logs/resource_events.jsonl"
  "logs/memory_retrieval.log"
)

python3 - <<'PY'
import os
from pathlib import Path

max_lines = int(os.getenv("LUCY_LOG_MAX_LINES", "20000"))
logs = [
    "logs/bus_metrics.jsonl",
    "logs/bridge_metrics.jsonl",
    "logs/resource_events.jsonl",
    "logs/memory_retrieval.log",
]
for path in logs:
    p = Path(path)
    if not p.exists():
        continue
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            p.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except Exception:
        pass
PY

echo "✅ Logs rotados (max ${MAX_LINES} líneas)"
