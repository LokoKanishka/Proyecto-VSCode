#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$PROJECT_DIR/.venv-web/bin/python3"
if [ ! -x "$PY" ]; then
  echo "[SmokeNoLLM] ERROR: no encuentro $PY" >&2
  exit 2
fi

echo "[SmokeNoLLM] levantando searxng (docker compose up -d)..."
if ! docker compose -f "$PROJECT_DIR/infra/searxng/docker-compose.yml" up -d; then
  echo "[SmokeNoLLM] ERROR: docker compose up falló" >&2
  docker compose -f "$PROJECT_DIR/infra/searxng/docker-compose.yml" ps >&2 || true
  docker compose -f "$PROJECT_DIR/infra/searxng/docker-compose.yml" logs --tail=120 >&2 || true
  exit 1
fi

export LUCY_WEB_NO_LLM=1

echo "[SmokeNoLLM] run_web_research() (sin LLM, debe terminar rápido)"
timeout 60s "$PY" - <<'PY'
from lucy_agents.web_agent import run_web_research
out = run_web_research("qué es el número áureo", model_id=None, max_results=5, verbosity=1)
print(out)
PY

echo "[SmokeNoLLM] OK"
