#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PY="$PROJECT_DIR/.venv-web/bin/python3"
if [ ! -x "$PY" ]; then
  echo "[QuickCheck] ERROR: no encuentro $PY (falta .venv-web)" >&2
  exit 2
fi

COMPOSE_FILE="$PROJECT_DIR/infra/searxng/docker-compose.yml"
docker compose -f "$COMPOSE_FILE" up -d >/dev/null

echo "[QuickCheck] CURL POST /search (24 líneas):"
timeout 12s curl -sS -i -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "q=numero aureo&format=json&language=es-AR&safesearch=1" \
  "http://127.0.0.1:8080/search" | sed -n '1,24p'
echo

echo "[QuickCheck] PY searx_search() (sin Ollama):"
timeout 30s "$PY" - <<'PY'
from lucy_agents.web_agent.web_search import searx_search
qs=["numero aureo","numero aureo argentina"]
res=searx_search(qs, base_url="http://127.0.0.1:8080", lang="es-AR", safesearch=1, timeout_s=12)
print("results=", len(res))
for r in res[:5]:
    print("-", (r.title or "")[:80], "|", r.url)
PY

echo "[QuickCheck] OK"
