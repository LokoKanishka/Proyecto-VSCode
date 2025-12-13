#!/usr/bin/env bash

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
