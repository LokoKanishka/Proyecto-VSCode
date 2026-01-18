#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# --- Diego client guard ---
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
export CHROME_PROFILE_NAME="${CHROME_PROFILE_NAME:-${CHATGPT_PROFILE_NAME}}"
export CHROME_DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
export CHROME_DIEGO_PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"

pre="$("$ROOT/scripts/chatgpt_diego_preflight.sh")"
CHROME_WID_HEX="$(printf '%s\n' "$pre" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
if [ -z "${CHROME_WID_HEX:-}" ]; then
  echo "ERROR_DIEGO_PREFLIGHT_NO_WID" >&2
  exit 3
fi
export CHATGPT_WID_HEX="$CHROME_WID_HEX"
export CHATGPT_WID_PIN_FILE="$CHROME_DIEGO_PIN_FILE"
export CHATGPT_ALLOW_ACTIVE_WINDOW=0
export CHATGPT_WID_PIN_ONLY=1
# --- end Diego client guard ---

cd "$ROOT"

STAMP="${VERIFY_A8_STAMP:-$(date +%Y%m%d_%H%M%S)_$RANDOM}"
LOG="/tmp/verify_a8_day_start.${STAMP}.log"
SUMMARY="/tmp/verify_a8_day_start.${STAMP}.summary.txt"

: >"$LOG"

if ! "$ROOT/scripts/lucy_day_start.sh" | tee -a "$LOG"; then
  echo "ERROR: lucy_day_start failed" >&2
  exit 1
fi

grep -q "LUCY_DAY_START_OK" "$LOG" || { echo "ERROR: missing LUCY_DAY_START_OK" >&2; exit 1; }
grep -q "VERIFY_WEB_SEARCH_SEARXNG_OK" "$LOG" || { echo "ERROR: missing VERIFY_WEB_SEARCH_SEARXNG_OK" >&2; exit 1; }
if ! grep -q "VERIFY_UI_DUMMY_PIPE_OK" "$LOG"; then
  grep -q "SKIP_UI_DUMMY_PIPE_STRICT=1" "$LOG" || { echo "ERROR: missing VERIFY_UI_DUMMY_PIPE_OK" >&2; exit 1; }
fi
grep -q "VERIFY_A5_PAID_SMOKE_OK" "$LOG" || { echo "ERROR: missing VERIFY_A5_PAID_SMOKE_OK" >&2; exit 1; }

if [[ -f "$ROOT/scripts/chatgpt_profile_paid_env.sh" ]]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/chatgpt_profile_paid_env.sh"
else
  echo "ERROR: missing chatgpt_profile_paid_env.sh" >&2
  exit 1
fi

export CHATGPT_ALLOW_ACTIVE_WINDOW="${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}"
export CHATGPT_WID_PIN_ONLY="${CHATGPT_WID_PIN_ONLY:-1}"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
if [[ -z "${CHATGPT_WID_PIN_FILE:-}" ]]; then
  export CHATGPT_WID_PIN_FILE="$ROOT/diagnostics/pins/chatgpt_diego.wid"
fi

THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-$ROOT/diagnostics/chatgpt/paid_test_thread.url}"
THREAD_FILE_URL=""
if [[ -f "${THREAD_FILE}" ]]; then
  THREAD_FILE_URL="$(head -n 1 "${THREAD_FILE}" | tr -d '\r')"
fi

PIN_FILE="${CHATGPT_WID_PIN_FILE:-/tmp/lucy_chatgpt_wid_pin_paid}"
PAID_WID="$(head -n 1 "${PIN_FILE}" 2>/dev/null | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
if [[ -z "${PAID_WID:-}" ]]; then
  PAID_WID="$(CHATGPT_TARGET=paid "$ROOT/scripts/chatgpt_get_wid.sh" 2>/dev/null || true)"
fi
CURRENT_URL=""
if [[ -n "${PAID_WID:-}" ]]; then
  CURRENT_URL="$("$ROOT/scripts/chatgpt_paid_get_url.sh" "${PAID_WID}" 2>/dev/null || true)"
fi

PAID_PID=""
if [[ -n "${PAID_WID:-}" ]]; then
  PAID_PID="$("$ROOT/scripts/x11_host_exec.sh" "wmctrl -lp | awk '\$1==\"${PAID_WID}\" {print \$3; exit}'" 2>/dev/null || true)"
fi

SEARX_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"

{
  echo "thread_file_url=${THREAD_FILE_URL}"
  echo "current_url=${CURRENT_URL}"
  echo "paid_pid=${PAID_PID}"
  echo "paid_wid=${PAID_WID}"
  echo "searx_url=${SEARX_URL}"
} > "${SUMMARY}"

if [[ -z "${THREAD_FILE_URL:-}" || -z "${CURRENT_URL:-}" ]]; then
  echo "VERIFY_A8_FAIL THREAD_CHANGED" >&2
  exit 1
fi
if [[ "${THREAD_FILE_URL}" != "${CURRENT_URL}" ]]; then
  echo "VERIFY_A8_FAIL THREAD_CHANGED" >&2
  exit 1
fi

echo "VERIFY_A8_OK"
