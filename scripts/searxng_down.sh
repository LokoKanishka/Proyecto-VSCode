#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/searxng/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no está en PATH. Saltando." >&2
  exit 1
fi

echo "Bajando SearXNG local (docker compose -f $COMPOSE_FILE down)..."
docker compose -f "$COMPOSE_FILE" down
echo "Listo."
