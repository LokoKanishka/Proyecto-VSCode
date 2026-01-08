#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NET_CHECK_SCRIPT="${NET_CHECK_SCRIPT:-$ROOT/scripts/net_check.sh}"
PUSH_REMOTE="${PUSH_REMOTE:-origin}"
PUSH_BRANCH="${PUSH_BRANCH:-main}"
BACKOFF="${PUSH_WHEN_NET_BACKOFF:-2 5 10 20 40}"
MAX_ATTEMPTS="${PUSH_WHEN_NET_MAX_ATTEMPTS:-}"
RUN_VERIFY_A7="${RUN_VERIFY_A7:-1}"

log() {
  printf '%s\n' "$*"
}

print_status() {
  log "== GIT STATUS =="
  git status -sb
  log "== GIT LOG -1 =="
  git log -1 --oneline
  log "== GIT REV-LIST =="
  if ! git rev-list --left-right --count "${PUSH_REMOTE}/${PUSH_BRANCH}...${PUSH_BRANCH}"; then
    return 1
  fi
}

net_check_with_backoff() {
  local attempt=1
  local -a delays=()
  read -r -a delays <<<"${BACKOFF}"
  local max_attempts="${MAX_ATTEMPTS}"
  if [[ -z "${max_attempts}" ]]; then
    max_attempts=$(( ${#delays[@]} + 1 ))
  fi

  while true; do
    log "NET_CHECK_ATTEMPT=${attempt}"
    if "${NET_CHECK_SCRIPT}"; then
      return 0
    fi
    if [[ "${attempt}" -ge "${max_attempts}" ]]; then
      return 1
    fi
    local delay="${delays[$((attempt - 1))]:-0}"
    log "NET_CHECK_RETRY_SLEEP=${delay}s"
    sleep "${delay}"
    attempt=$((attempt + 1))
  done
}

main() {
  log "PUSH_WHEN_NET_START"

  if ! print_status; then
    echo "PUSH_WHEN_NET_FAIL(reason=git_status_failed)"
    return 1
  fi

  local counts
  if ! counts="$(git rev-list --left-right --count "${PUSH_REMOTE}/${PUSH_BRANCH}...${PUSH_BRANCH}")"; then
    echo "PUSH_WHEN_NET_FAIL(reason=rev_list_failed)"
    return 1
  fi
  local behind=""
  local ahead=""
  read -r behind ahead <<<"${counts}"
  if [[ -z "${behind}" || -z "${ahead}" ]]; then
    echo "PUSH_WHEN_NET_FAIL(reason=rev_list_parse_failed)"
    return 1
  fi

  log "AHEAD_BEHIND ahead=${ahead} behind=${behind}"

  if [[ "${ahead}" -eq 0 ]]; then
    echo "PUSH_WHEN_NET_OK reason=up_to_date"
    return 0
  fi

  if [[ ! -x "${NET_CHECK_SCRIPT}" ]]; then
    echo "PUSH_WHEN_NET_FAIL(reason=net_check_missing)"
    return 1
  fi

  if ! net_check_with_backoff; then
    echo "PUSH_WHEN_NET_FAIL(reason=net_check_failed)"
    return 1
  fi

  log "PUSH_START remote=${PUSH_REMOTE} branch=${PUSH_BRANCH}"
  if ! GIT_TERMINAL_PROMPT=0 git push "${PUSH_REMOTE}" "${PUSH_BRANCH}"; then
    echo "PUSH_WHEN_NET_FAIL(reason=push_failed)"
    return 1
  fi

  if ! GIT_TERMINAL_PROMPT=0 git fetch "${PUSH_REMOTE}"; then
    echo "PUSH_WHEN_NET_FAIL(reason=fetch_failed)"
    return 1
  fi

  local local_head
  local remote_head
  local_head="$(git rev-parse "${PUSH_BRANCH}")"
  remote_head="$(git rev-parse "${PUSH_REMOTE}/${PUSH_BRANCH}")"
  log "POST_PUSH_HEAD local=${local_head} remote=${remote_head}"
  if [[ "${local_head}" != "${remote_head}" ]]; then
    echo "PUSH_WHEN_NET_FAIL(reason=post_push_mismatch)"
    return 1
  fi

  if [[ "${RUN_VERIFY_A7}" -eq 1 ]]; then
    log "RUN_VERIFY_A7=1"
    if ! "$ROOT/scripts/verify_a7_all.sh"; then
      echo "PUSH_WHEN_NET_FAIL(reason=verify_a7_failed)"
      return 1
    fi
  else
    log "SKIP_VERIFY_A7 reason=disabled"
  fi

  echo "PUSH_WHEN_NET_OK"
}

main "$@"
