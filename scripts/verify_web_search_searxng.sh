#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"

list_out="$(python3 -m lucy_agents.action_router --list)"
if ! grep -qx "web_search" <<<"${list_out}"; then
  echo "ERROR: web_search missing" >&2
  exit 1
fi

desc="$(python3 -m lucy_agents.action_router --describe web_search)"
python3 - <<'PY' "$desc"
import json
import sys

raw = sys.argv[1]
obj = json.loads(raw)
req = obj.get("payload", {}).get("required") or []
path = obj.get("path", "")
if "query" not in req:
    raise SystemExit(1)
if "LOCAL" not in path:
    raise SystemExit(1)
PY

if ! curl -fsS --max-time 5 "${SEARXNG_URL}/healthz" >/dev/null 2>&1; then
  if ! curl -fsS --max-time 5 "${SEARXNG_URL}/" >/dev/null 2>&1; then
    echo "SearxNG no está activo. Levantalo con: docker compose -f infra/searxng/docker-compose.yml up -d" >&2
    exit 2
  fi
fi

payload='{"query":"wikipedia","num_results":5,"language":"es","safesearch":0}'
out="$(python3 -m lucy_agents.action_router web_search "${payload}")"
python3 - <<'PY' "$out"
import json
import sys

raw = sys.argv[1]
obj = json.loads(raw)
if not obj.get("ok"):
    raise SystemExit(1)
result = obj.get("result") or {}
for key in ("query", "engine", "searxng_url", "results", "errors"):
    if key not in result:
        raise SystemExit(1)
if result.get("engine") != "searxng":
    raise SystemExit(1)
if not isinstance(result.get("results"), list):
    raise SystemExit(1)
if not isinstance(result.get("errors"), list):
    raise SystemExit(1)
if result.get("errors"):
    print("ERROR: web_search returned errors", file=sys.stderr)
    raise SystemExit(1)
PY

echo "VERIFY_WEB_SEARCH_SEARXNG_OK"
