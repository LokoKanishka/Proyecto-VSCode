#!/bin/bash
set -euo pipefail

PORT="${LUCY_WEB_PORT:-5000}"
RESOURCE_LOG="logs/resource_events.jsonl"
SMOKE_LOG="/tmp/lucy_resource_smoke.log"

mkdir -p "$(dirname "$RESOURCE_LOG")"

python3 <<'PY'
import json, time, pathlib
record = {
    "timestamp": time.time(),
    "event": "gpu_pressure",
    "data": {"usage_pct": 0.92, "note": "Smoke test"},
}
path = pathlib.Path("logs/resource_events.jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("a", encoding="utf-8") as fd:
    fd.write(json.dumps(record) + "\n")
PY

resource_output=$(curl -sS "http://localhost:${PORT}/api/resource_events")
echo "$resource_output"
printf "%s" "$resource_output" | python3 <<'PY'
import json, sys
data = json.loads(sys.stdin.read())
summary = data.get("summary", {})
if summary.get("gpu") is None or summary["gpu"] < 0.9:
    raise SystemExit("GPU summary missing or too low")
PY

curl -sS "http://localhost:${PORT}/api/plan_log" > /tmp/lucy_plan_log.json
curl -sS "http://localhost:${PORT}/api/memory_summary" > /tmp/lucy_memory_summary.json

echo "GPU pressure smoke completed; logs in /tmp/lucy_plan_log.json and /tmp/lucy_memory_summary.json"
