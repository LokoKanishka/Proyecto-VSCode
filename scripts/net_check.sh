#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DNS_HOST="${NETCHECK_DNS_HOST:-github.com}"
GIT_REMOTE="${NETCHECK_GIT_REMOTE:-origin}"
GIT_TIMEOUT="${NETCHECK_GIT_TIMEOUT:-6}"

log() {
  printf '%s\n' "$*"
}

rc=0

if command -v getent >/dev/null 2>&1; then
  if getent hosts "${DNS_HOST}" >/dev/null 2>&1; then
    log "NET_CHECK_DNS_OK method=getent host=${DNS_HOST}"
  else
    log "NET_CHECK_DNS_FAIL method=getent host=${DNS_HOST}"
    rc=2
  fi
elif command -v nslookup >/dev/null 2>&1; then
  if nslookup "${DNS_HOST}" >/dev/null 2>&1; then
    log "NET_CHECK_DNS_OK method=nslookup host=${DNS_HOST}"
  else
    log "NET_CHECK_DNS_FAIL method=nslookup host=${DNS_HOST}"
    rc=2
  fi
else
  log "NET_CHECK_DNS_FAIL reason=no_getent_or_nslookup host=${DNS_HOST}"
  rc=2
fi

if [[ "${rc}" -eq 0 ]]; then
  if command -v timeout >/dev/null 2>&1; then
    if timeout "${GIT_TIMEOUT}" GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askpass= ls-remote --heads "${GIT_REMOTE}" >/dev/null 2>&1; then
      log "NET_CHECK_GIT_OK remote=${GIT_REMOTE}"
    else
      log "NET_CHECK_GIT_FAIL remote=${GIT_REMOTE}"
      rc=3
    fi
  else
    if GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askpass= ls-remote --heads "${GIT_REMOTE}" >/dev/null 2>&1; then
      log "NET_CHECK_GIT_OK remote=${GIT_REMOTE} timeout=none"
    else
      log "NET_CHECK_GIT_FAIL remote=${GIT_REMOTE} timeout=none"
      rc=3
    fi
  fi
fi

if [[ "${rc}" -eq 0 ]]; then
  log "NET_CHECK_OK"
else
  log "NET_CHECK_FAIL rc=${rc}"
fi

exit "${rc}"
