#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PY="$PROJECT_DIR/.venv-web/bin/python3"
if [ ! -x "$PY" ]; then
  echo "[Smoke] ERROR: no encuentro $PY (falta .venv-web)" >&2
  exit 2
fi

COMPOSE_FILE="$PROJECT_DIR/infra/searxng/docker-compose.yml"
echo "[Smoke] levantando searxng (docker compose up -d)..."
if ! docker compose -f "$COMPOSE_FILE" up -d; then
  echo "[Smoke] ERROR: docker compose up falló" >&2
  docker compose -f "$COMPOSE_FILE" ps >&2 || true
  docker compose -f "$COMPOSE_FILE" logs --tail=120 >&2 || true
  exit 1
fi

echo "[Smoke] CURL POST /search (primeras 12 líneas):"
timeout 12s curl -sS -i -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "q=numero aureo&format=json&language=es-AR&safesearch=1" \
  "http://127.0.0.1:8080/search" | sed -n '1,12p'
echo

echo "[Smoke] web_answer() (searxng, sin fetch, sin Ollama):"
timeout 30s "$PY" - <<'PY'
from lucy_agents.web_agent.web_search import web_answer

def fallback(_q, _max):
    return []  # si searxng anda, no se usa

payload = web_answer(
    question="numero aureo",
    search_fn=fallback,
    provider="searxng",
    searxng_url="http://127.0.0.1:8080",
    lang="es-AR",
    safesearch=1,
    top_k=5,
    fetch_top_n=0,
    timeout_s=12,
)

used = payload.get("used_provider")
res = payload.get("results") or payload.get("results_list") or []

print("used_provider=", used)
print("results_len=", len(res))

if used != "searxng":
    raise SystemExit("ERROR: used_provider != searxng")
if len(res) == 0:
    raise SystemExit("ERROR: 0 resultados")

for r in res[:5]:
    title = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "")
    url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else "")
    print("-", str(title)[:90], "|", url)
PY

echo "[Smoke] OK"
