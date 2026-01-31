#!/bin/bash
set -euo pipefail

PORT="${LUCY_WEB_PORT:-5000}"
URL="http://localhost:${PORT}/api/resource_events"

echo "Consultando endpoint de recursos: ${URL}"
response=$(curl -sS "${URL}")
if [[ -z "$response" ]]; then
  echo "No se obtuvo respuesta."
  exit 1
fi

echo "$response" | jq '.'
echo "Recurso terminado con éxito."
