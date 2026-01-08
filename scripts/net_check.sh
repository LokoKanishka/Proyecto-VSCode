#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DNS_HOST="${NETCHECK_DNS_HOST:-github.com}"
GIT_REMOTE="${NETCHECK_GIT_REMOTE:-origin}"
GIT_TIMEOUT="${NETCHECK_GIT_TIMEOUT:-6}"
ERR_TAIL_LINES="${NETCHECK_ERR_TAIL_LINES:-40}"

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
  git_err_file="$(mktemp /tmp/net_check_lsremote.XXXXXX)"
  trap 'rm -f "${git_err_file}"' EXIT

  if command -v timeout >/dev/null 2>&1; then
    if timeout "${GIT_TIMEOUT}" env GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askpass= -c credential.interactive=never ls-remote --heads "${GIT_REMOTE}" >/dev/null 2>"${git_err_file}"; then
      log "NET_CHECK_GIT_OK remote=${GIT_REMOTE} timeout=${GIT_TIMEOUT}"
    else
      git_rc=$?
      if [[ "${git_rc}" -eq 124 ]]; then
        log "NET_CHECK_GIT_TIMEOUT remote=${GIT_REMOTE} timeout=${GIT_TIMEOUT} rc=124"
        rc=124
      else
        log "NET_CHECK_GIT_FAIL remote=${GIT_REMOTE} rc=${git_rc}"
        rc=3
      fi
      if [[ -s "${git_err_file}" ]]; then
        log "NET_CHECK_GIT_ERR_TAIL"
        tail -n "${ERR_TAIL_LINES}" "${git_err_file}" || true
      else
        log "NET_CHECK_GIT_ERR_TAIL_EMPTY"
      fi
    fi
  else
    if env GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askpass= -c credential.interactive=never ls-remote --heads "${GIT_REMOTE}" >/dev/null 2>"${git_err_file}"; then
      log "NET_CHECK_GIT_OK remote=${GIT_REMOTE} timeout=none"
    else
      git_rc=$?
      log "NET_CHECK_GIT_FAIL remote=${GIT_REMOTE} rc=${git_rc} timeout=none"
      rc=3
      if [[ -s "${git_err_file}" ]]; then
        log "NET_CHECK_GIT_ERR_TAIL"
        tail -n "${ERR_TAIL_LINES}" "${git_err_file}" || true
      else
        log "NET_CHECK_GIT_ERR_TAIL_EMPTY"
      fi
    fi
  fi
fi

if [[ "${rc}" -eq 0 ]]; then
  log "NET_CHECK_OK"
else
  log "NET_CHECK_FAIL rc=${rc}"
fi

exit "${rc}"
