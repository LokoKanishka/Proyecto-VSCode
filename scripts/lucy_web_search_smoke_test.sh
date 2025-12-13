#!/usr/bin/env bash

# Auto-activar venv web si existe (para que el smoke sea portable)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_DIR/.venv-web/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$PROJECT_DIR/.venv-web/bin/activate"
fi


set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/searxng/docker-compose.yml"

if command -v docker >/dev/null 2>&1; then
  echo "[Smoke] Intentando levantar SearXNG local (si ya está corriendo, se reutiliza)..."
  docker compose -f "$COMPOSE_FILE" up -d || echo "[Smoke] No se pudo levantar SearXNG, seguimos con fallback."
else
  echo "[Smoke] Docker no está disponible. Se usará el backend de fallback."
fi

echo "[Smoke] Ejecutando consulta de prueba (\"qué es el número áureo\")..."
python3 - << 'PY'
from lucy_agents.web_agent.agent import run_web_research

answer = run_web_research(
    task="qué es el número áureo",
    max_results=5,
    verbosity=1,
)
print("\n--- Respuesta ---\n")
print(answer)
PY
