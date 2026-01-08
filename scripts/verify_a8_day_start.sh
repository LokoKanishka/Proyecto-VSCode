#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="${VERIFY_A8_STAMP:-$(date +%Y%m%d_%H%M%S)_$RANDOM}"
LOG="/tmp/verify_a8_day_start.${STAMP}.log"

: >"$LOG"

if ! "$ROOT/scripts/lucy_day_start.sh" | tee -a "$LOG"; then
  echo "ERROR: lucy_day_start failed" >&2
  exit 1
fi

grep -q "LUCY_DAY_START_OK" "$LOG" || { echo "ERROR: missing LUCY_DAY_START_OK" >&2; exit 1; }
grep -q "VERIFY_WEB_SEARCH_SEARXNG_OK" "$LOG" || { echo "ERROR: missing VERIFY_WEB_SEARCH_SEARXNG_OK" >&2; exit 1; }
grep -q "VERIFY_UI_DUMMY_PIPE_OK" "$LOG" || { echo "ERROR: missing VERIFY_UI_DUMMY_PIPE_OK" >&2; exit 1; }
grep -q "VERIFY_A5_PAID_SMOKE_OK" "$LOG" || { echo "ERROR: missing VERIFY_A5_PAID_SMOKE_OK" >&2; exit 1; }

echo "VERIFY_A8_OK"
