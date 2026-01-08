#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST_DOCKER="$ROOT/scripts/host_docker.sh"
SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"
SEARXNG_COMPOSE_FILE="${SEARXNG_COMPOSE_FILE:-infra/searxng/docker-compose.yml}"
SEARXNG_HEALTH_TIMEOUT_SEC="${SEARXNG_HEALTH_TIMEOUT_SEC:-30}"

searxng_reachable() {
  if curl -fsS --max-time 5 "${SEARXNG_URL}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  curl -fsS --max-time 5 "${SEARXNG_URL}/" >/dev/null 2>&1
}

ensure_searxng_up() {
  if searxng_reachable; then
    return 0
  fi

  echo "WARN: SearxNG no está activo. Intentando levantarlo..." >&2
  if ! "$HOST_DOCKER" compose -f "${SEARXNG_COMPOSE_FILE}" up -d; then
    echo "ERROR: no se pudo ejecutar docker compose up -d" >&2
    exit 3
  fi

  for _ in $(seq 1 "${SEARXNG_HEALTH_TIMEOUT_SEC}"); do
    if searxng_reachable; then
      return 0
    fi
    sleep 1
  done

  echo "ERROR: SearxNG no está activo. Levantalo con: docker compose -f ${SEARXNG_COMPOSE_FILE} up -d" >&2
  "$HOST_DOCKER" compose -f "${SEARXNG_COMPOSE_FILE}" ps || true
  "$HOST_DOCKER" compose -f "${SEARXNG_COMPOSE_FILE}" logs --tail 80 || true
  exit 3
}

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

ensure_searxng_up

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
