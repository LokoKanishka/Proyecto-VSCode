#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d_%H%M%S)_$RANDOM"
LOG="/tmp/lucy_day_start.${STAMP}.log"

: >"$LOG"
exec > >(tee -a "$LOG") 2>&1

log() {
  printf '%s\n' "$*"
}

log "LUCY_DAY_START_START stamp=${STAMP}"

if [[ -f "$ROOT/scripts/chatgpt_profile_paid_env.sh" ]]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/chatgpt_profile_paid_env.sh"
else
  echo "ERROR: missing chatgpt_profile_paid_env.sh" >&2
  exit 2
fi

export CHATGPT_PAID_THREAD_STRICT=1

SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"

searxng_reachable() {
  if curl -fsS --max-time 5 "${SEARXNG_URL}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  curl -fsS --max-time 5 "${SEARXNG_URL}/" >/dev/null 2>&1
}

log "== SERVICES =="
if ! DEBUG=1 "$ROOT/scripts/local_services_up.sh"; then
  echo "ERROR: local_services_up failed" >&2
  exit 3
fi
if ! searxng_reachable; then
  echo "ERROR: SearxNG no responde en ${SEARXNG_URL}" >&2
  exit 3
fi

log "== PAID ENSURE =="
ensure_out="$("$ROOT/scripts/chatgpt_paid_ensure_chatgpt.sh" 2>&1)" || {
  echo "$ensure_out" >&2
  echo "ERROR: chatgpt_paid_ensure_chatgpt failed" >&2
  exit 4
}
log "$ensure_out"
PAID_WID="$(printf '%s\n' "$ensure_out" | awk -F= '/PAID_CHATGPT_WID=/{print $2}' | tail -n 1)"
PAID_PID="$(printf '%s\n' "$ensure_out" | awk -F= '/PAID_CHATGPT_PID=/{print $2}' | tail -n 1)"
if [[ -z "${PAID_WID:-}" ]]; then
  echo "ERROR: missing PAID_CHATGPT_WID" >&2
  exit 4
fi

log "== THREAD ENSURE =="
set +e
THREAD_URL="$(CHATGPT_TARGET=paid CHATGPT_PAID_ENSURE_CALLER=1 PAID_CHATGPT_WID="${PAID_WID}" PAID_CHATGPT_PID="${PAID_PID}" "$ROOT/scripts/chatgpt_paid_ensure_test_thread.sh" 2>&1)"
thread_rc=$?
set -e
log "$THREAD_URL"
if [[ "${thread_rc}" -ne 0 ]]; then
  echo "ERROR: chatgpt_paid_ensure_test_thread failed rc=${thread_rc}" >&2
  exit 5
fi
THREAD_URL="$(printf '%s\n' "$THREAD_URL" | tail -n 1)"
if [[ -z "${THREAD_URL:-}" ]]; then
  echo "ERROR: empty thread URL" >&2
  exit 5
fi

THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-/tmp/lucy_chatgpt_paid_test_thread.url}"
if [[ ! -f "${THREAD_FILE}" ]]; then
  echo "ERROR: thread file missing at ${THREAD_FILE}" >&2
  exit 5
fi
THREAD_FILE_URL="$(head -n 1 "${THREAD_FILE}" | tr -d '\r')"
if [[ "${THREAD_FILE_URL}" != "${THREAD_URL}" ]]; then
  echo "ERROR: thread file mismatch file=${THREAD_FILE_URL} expected=${THREAD_URL}" >&2
  exit 5
fi

log "== THREAD CHECK =="
CUR_URL="$("$ROOT/scripts/chatgpt_paid_get_url.sh" "${PAID_WID}" 2>/dev/null || true)"
if [[ "${CUR_URL}" != "${THREAD_URL}" ]]; then
  fore_dir="/tmp/lucy_chatgpt_bridge/$(date +%F)/DAY_START_$(date +%s)_$RANDOM"
  mkdir -p "$fore_dir"
  printf '%s\n' "${CUR_URL}" > "$fore_dir/url.txt" 2>/dev/null || true
  printf '%s\n' "${THREAD_URL}" > "$fore_dir/thread_url.txt" 2>/dev/null || true
  printf '%s\n' "${PAID_WID}" > "$fore_dir/active_wid.txt" 2>/dev/null || true
  echo "FORENSICS_DIR=${fore_dir}" >&2
  echo "ERROR: WRONG_THREAD cur=${CUR_URL} expected=${THREAD_URL}" >&2
  exit 6
fi

log "== PIN ROBUST =="
WID_HEX="$(CHATGPT_TARGET=paid "$ROOT/scripts/chatgpt_get_wid.sh")"
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR: chatgpt_get_wid returned empty" >&2
  exit 6
fi
pin_out="$(CHATGPT_TARGET=paid CHATGPT_WID_HEX="${WID_HEX}" "$ROOT/scripts/chatgpt_pin_wid.sh" 2>&1)" || {
  echo "$pin_out" >&2
  echo "ERROR: chatgpt_pin_wid failed" >&2
  exit 6
}
log "$pin_out"

PIN_FILE="${CHATGPT_WID_PIN_FILE:-/tmp/lucy_chatgpt_wid_pin_paid}"
if [[ "${PIN_FILE}" != /tmp/* ]]; then
  echo "ERROR: pin file not in /tmp (PIN_FILE=${PIN_FILE})" >&2
  exit 6
fi
if [[ ! -f "${PIN_FILE}" ]]; then
  echo "ERROR: pin file missing at ${PIN_FILE}" >&2
  exit 6
fi
PIN_WID="$(head -n 1 "${PIN_FILE}" | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
if [[ -z "${PIN_WID:-}" ]]; then
  echo "ERROR: pin file empty at ${PIN_FILE}" >&2
  exit 6
fi

log "== SMOKE DUMMY =="
"$ROOT/scripts/verify_ui_dummy_pipe.sh"

log "== SMOKE WEB_SEARCH =="
"$ROOT/scripts/verify_web_search_searxng.sh"

log "== SMOKE A5 PAID =="
CHATGPT_TARGET=paid "$ROOT/scripts/verify_a5_paid_smoke.sh"

log "LUCY_DAY_START_OK stamp=${STAMP}"
