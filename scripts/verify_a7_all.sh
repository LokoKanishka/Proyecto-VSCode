#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="${VERIFY_A7_STAMP:-$(date +%Y%m%d_%H%M%S)_$RANDOM}"
LOG="/tmp/verify_a7_all.a37.${STAMP}.log"

: >"$LOG"
exec > >(tee -a "$LOG") 2>&1

echo "VERIFY_A7_ALL_START stamp=${STAMP}"

rc=0

run_step() {
  local name="$1"
  shift
  echo "== ${name} =="
  if ! "$@"; then
    echo "ERROR: ${name} failed"
    rc=1
  fi
}

run_step "DUMMY" env CHATGPT_TARGET=dummy "$ROOT/scripts/verify_ui_dummy_pipe.sh"
run_step "WEB_SEARCH" "$ROOT/scripts/verify_web_search_searxng.sh"
run_step "A6_PAID_1" env CHATGPT_TARGET=paid "$ROOT/scripts/verify_a6_all.sh"
run_step "A6_PAID_2" env CHATGPT_TARGET=paid "$ROOT/scripts/verify_a6_all.sh"

if [[ "$rc" -ne 0 ]]; then
  echo "ERROR: VERIFY_A7_ALL_FAIL"
  echo "== FORENSICS (latest 3) =="
  daydir="/tmp/lucy_chatgpt_bridge/$(date +%F)"
  ls -td "$daydir"/REQ_* 2>/dev/null | head -n 3 || true
  exit 1
fi

echo "VERIFY_A7_ALL_OK"
