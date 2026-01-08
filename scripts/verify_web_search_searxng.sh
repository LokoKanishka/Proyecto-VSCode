#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST_DOCKER="$ROOT/scripts/host_docker.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"
SEARXNG_COMPOSE_FILE="${SEARXNG_COMPOSE_FILE:-$ROOT/infra/searxng/docker-compose.yml}"
SEARXNG_HEALTH_TIMEOUT_SEC="${SEARXNG_HEALTH_TIMEOUT_SEC:-30}"
SEARXNG_HOST_ONLY=0

searxng_reachable() {
  if curl -fsS --max-time 5 "${SEARXNG_URL}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  curl -fsS --max-time 5 "${SEARXNG_URL}/" >/dev/null 2>&1
}

searxng_reachable_host() {
  "$HOST_EXEC" "bash -lc 'curl -fsS --max-time 5 \"${SEARXNG_URL}/healthz\" >/dev/null 2>&1 || curl -fsS --max-time 5 \"${SEARXNG_URL}/\" >/dev/null 2>&1'" >/dev/null 2>&1
}

ensure_searxng_up() {
  if searxng_reachable; then
    return 0
  fi
  if searxng_reachable_host; then
    SEARXNG_HOST_ONLY=1
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
    if searxng_reachable_host; then
      SEARXNG_HOST_ONLY=1
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
if [[ "${SEARXNG_HOST_ONLY}" -eq 1 ]]; then
  payload_b64="$(printf '%s' "${payload}" | base64 -w0 2>/dev/null || python3 - <<'PY' "${payload}"
import base64
import sys
data = sys.argv[1].encode("utf-8")
print(base64.b64encode(data).decode("ascii"))
PY
)"
  payload_b64_q="$(printf '%q' "${payload_b64}")"
  py='import base64,os,subprocess,sys; payload=base64.b64decode(os.environ.get("SEARXNG_PAYLOAD_B64","").encode("ascii")).decode("utf-8"); proc=subprocess.run(["python3","-m","lucy_agents.action_router","web_search",payload], text=True, capture_output=True, env=dict(os.environ)); sys.stdout.write(proc.stdout); sys.stderr.write(proc.stderr); sys.exit(proc.returncode)'
  py_q="$(printf '%q' "${py}")"
  out="$("$HOST_EXEC" "bash -lc 'cd ${ROOT} && SEARXNG_URL=\"${SEARXNG_URL}\" SEARXNG_PAYLOAD_B64=${payload_b64_q} python3 -c ${py_q}'")"
else
  out="$(python3 -m lucy_agents.action_router web_search "${payload}")"
fi
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
