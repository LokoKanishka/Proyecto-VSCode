#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() {
  printf '%s\n' "$*"
}

log "VERIFY_NET_CHECK_START"

if command -v timeout >/dev/null 2>&1; then
  if timeout 1 env NETCHECK_PROBE=1 bash -lc 'exit 0' >/dev/null 2>&1; then
    log "VERIFY_NET_CHECK_TIMEOUT_ENV_OK"
  else
    log "VERIFY_NET_CHECK_TIMEOUT_ENV_FAIL"
  fi
else
  log "VERIFY_NET_CHECK_TIMEOUT_ENV_SKIP reason=no_timeout"
fi

if "$ROOT/scripts/net_check.sh"; then
  log "VERIFY_NET_CHECK_OK"
else
  rc=$?
  log "VERIFY_NET_CHECK_FAIL rc=${rc}"
  exit 1
fi
