#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST_DOCKER="$ROOT/scripts/host_docker.sh"
SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"
SEARXNG_COMPOSE_FILE="${SEARXNG_COMPOSE_FILE:-$ROOT/infra/searxng/docker-compose.yml}"
SEARXNG_HEALTH_TIMEOUT_SEC="${SEARXNG_HEALTH_TIMEOUT_SEC:-30}"

log() {
  [[ "${DEBUG:-0}" == "1" ]] && echo "$*" >&2
}

searxng_reachable() {
  if curl -fsS --max-time 5 "${SEARXNG_URL}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  curl -fsS --max-time 5 "${SEARXNG_URL}/" >/dev/null 2>&1
}

if searxng_reachable; then
  log "SearxNG already up: ${SEARXNG_URL}"
  exit 0
fi

log "Starting SearxNG (compose: ${SEARXNG_COMPOSE_FILE})"
if ! "$HOST_DOCKER" compose -f "${SEARXNG_COMPOSE_FILE}" up -d; then
  echo "ERROR: no se pudo ejecutar docker compose up -d" >&2
  exit 3
fi

for _ in $(seq 1 "${SEARXNG_HEALTH_TIMEOUT_SEC}"); do
  if searxng_reachable; then
    log "SearxNG ready: ${SEARXNG_URL}"
    exit 0
  fi
  sleep 1
done

echo "ERROR: SearxNG no estuvo listo tras ${SEARXNG_HEALTH_TIMEOUT_SEC}s" >&2
"$HOST_DOCKER" compose -f "${SEARXNG_COMPOSE_FILE}" ps || true
exit 3
