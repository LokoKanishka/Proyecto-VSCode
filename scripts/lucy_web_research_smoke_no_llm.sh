#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$PROJECT_DIR/.venv-web/bin/python3"
if [ ! -x "$PY" ]; then
  echo "[SmokeNoLLM] ERROR: no encuentro $PY" >&2
  exit 2
fi

docker compose -f "$PROJECT_DIR/infra/searxng/docker-compose.yml" up -d >/dev/null

export LUCY_WEB_NO_LLM=1

echo "[SmokeNoLLM] run_web_research() (sin LLM, debe terminar rápido)"
timeout 60s "$PY" - <<'PY'
from lucy_agents.web_agent import run_web_research
out = run_web_research("qué es el número áureo", model_id=None, max_results=5, verbosity=1)
print(out)
PY

echo "[SmokeNoLLM] OK"
