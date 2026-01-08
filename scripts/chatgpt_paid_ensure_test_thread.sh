#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
PAID_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_chatgpt.sh"
GET_URL="$ROOT/scripts/chatgpt_paid_get_url.sh"
SEND="$ROOT/scripts/chatgpt_ui_send_x11.sh"

CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
if [[ "${CHATGPT_TARGET}" != "paid" ]]; then
  echo "ERROR: chatgpt_paid_ensure_test_thread requiere CHATGPT_TARGET=paid" >&2
  exit 2
fi

LOG_PATH="${CHATGPT_PAID_THREAD_LOG:-/tmp/paid_ensure_thread.log}"
mkdir -p "$(dirname "$LOG_PATH")"
: >"$LOG_PATH"

log() {
  printf '%s\n' "$*" >>"$LOG_PATH"
}

THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-$HOME/.cache/lucy_chatgpt_paid_test_thread.url}"
STRICT_THREAD="${CHATGPT_PAID_THREAD_STRICT:-0}"
ensure_thread_file() {
  local f="$1"
  local dir
  dir="$(dirname "$f")"
  mkdir -p "$dir" 2>/dev/null || true
  if [[ -e "$f" ]]; then
    dd if=/dev/null of="$f" 2>/dev/null || return 1
  else
    local tmp
    tmp="$(mktemp "$dir/.threadwrite.XXXX" 2>/dev/null)" || return 1
    rm -f "$tmp" 2>/dev/null || true
  fi
  return 0
}
if ! ensure_thread_file "$THREAD_FILE"; then
  THREAD_FILE="/tmp/lucy_chatgpt_paid_test_thread.url"
  mkdir -p "$(dirname "$THREAD_FILE")" 2>/dev/null || true
  log "WARN: THREAD_FILE not writable, using ${THREAD_FILE}"
fi
MARKER_MSG="${CHATGPT_PAID_THREAD_MARKER:-LUCY_TEST_THREAD_DO_NOT_DELETE}"
BASE_URL="${CHATGPT_PAID_THREAD_BASE_URL:-https://chatgpt.com/}"
OPEN_NEW_TAB="${CHATGPT_PAID_OPEN_NEW_TAB:-0}"

dump_forensics() {
  local dir
  dir="/tmp/lucy_chatgpt_bridge/$(date +%F)/PAID_ENSURE_$(date +%s)_$RANDOM"
  mkdir -p "$dir"
  printf '%s\n' "${1:-}" > "$dir/url.txt" 2>/dev/null || true
  printf '%s\n' "${2:-}" > "$dir/thread_url.txt" 2>/dev/null || true
  "$HOST_EXEC" "wmctrl -lp" > "$dir/wmctrl_lp.txt" 2>/dev/null || true
  printf '%s\n' "${3:-}" > "$dir/active_wid.txt" 2>/dev/null || true
  log "FORENSICS_DIR=${dir}"
}

navigate_url() {
  local wid="$1"
  local url="$2"
  local wid_dec
  wid_dec="$(printf "%d" "$wid" 2>/dev/null || echo 0)"
  [[ "${wid_dec}" -gt 0 ]] || return 1
  "$HOST_EXEC" "wmctrl -ia ${wid}" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool windowactivate --sync ${wid_dec}" >/dev/null 2>&1 || true
  "$HOST_EXEC" "sleep 0.12" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool key --window ${wid_dec} ctrl+l" >/dev/null 2>&1 || true
  "$HOST_EXEC" "sleep 0.05" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool type --window ${wid_dec} '${url}'" >/dev/null 2>&1 || true
  if [[ "${OPEN_NEW_TAB}" -eq 1 ]]; then
    "$HOST_EXEC" "xdotool key --window ${wid_dec} alt+Return" >/dev/null 2>&1 || true
  else
    "$HOST_EXEC" "xdotool key --window ${wid_dec} Return" >/dev/null 2>&1 || true
  fi
}

valid_thread_url() {
  local url="$1"
  [[ -n "${url:-}" ]] || return 1
  [[ "${url}" == http*://* ]] || return 1
  if [[ "${url}" == "${BASE_URL}" ]] || [[ "${url}" == "${BASE_URL%/}" ]]; then
    return 1
  fi
  return 0
}

ensure_paid_window() {
  local wid=""
  if [[ -n "${PAID_CHATGPT_WID:-}" ]]; then
    wid="${PAID_CHATGPT_WID}"
    if [[ -n "${wid:-}" ]]; then
      printf '%s\n' "$wid"
      return 0
    fi
  fi
  if [[ "${CHATGPT_PAID_ENSURE_CALLER:-0}" -ne 1 ]]; then
    if [[ -x "$PAID_ENSURE" ]]; then
      ensure_out="$("$PAID_ENSURE" 2>/dev/null || true)"
      wid="$(printf '%s\n' "$ensure_out" | awk -F= '/PAID_CHATGPT_WID=/{print $2}' | tail -n 1)"
      if [[ -n "${wid:-}" ]]; then
        printf '%s\n' "$wid"
        return 0
      fi
    fi
  fi
  "$GET_WID" 2>/dev/null || true
}

THREAD_URL=""
if [[ -f "$THREAD_FILE" ]]; then
  THREAD_URL="$(head -n 1 "$THREAD_FILE" | tr -d '\r')"
  if [[ -n "${THREAD_URL:-}" ]]; then
    log "THREAD_FILE_OK=${THREAD_URL}"
  fi
fi

WID_HEX="$(ensure_paid_window)"
if [[ -z "${WID_HEX:-}" ]]; then
  log "ERROR: no WID for paid"
  dump_forensics "" "${THREAD_URL}" ""
  echo "ERROR: no WID for paid" >&2
  echo "PAID_THREAD_LOG=$LOG_PATH" >&2
  exit 3
fi

if [[ -n "${THREAD_URL:-}" ]]; then
  navigate_url "$WID_HEX" "$THREAD_URL" || true
  sleep 0.8
  cur_url="$("$GET_URL" "$WID_HEX" 2>/dev/null || true)"
  if [[ "${cur_url}" != "${THREAD_URL}" ]]; then
    navigate_url "$WID_HEX" "$THREAD_URL" || true
    sleep 0.8
    cur_url="$("$GET_URL" "$WID_HEX" 2>/dev/null || true)"
  fi
  if [[ "${cur_url}" != "${THREAD_URL}" ]]; then
    if [[ "${STRICT_THREAD}" -eq 1 ]]; then
      log "ERROR: WRONG_THREAD cur=${cur_url} expected=${THREAD_URL}"
      dump_forensics "${cur_url}" "${THREAD_URL}" "${WID_HEX}"
      echo "ERROR: WRONG_THREAD cur=${cur_url} expected=${THREAD_URL}" >&2
      echo "PAID_THREAD_LOG=$LOG_PATH" >&2
      exit 6
    fi
    log "WARN: thread URL mismatch cur=${cur_url} expected=${THREAD_URL}"
    dump_forensics "${cur_url}" "${THREAD_URL}" "${WID_HEX}"
    rm -f "$THREAD_FILE" 2>/dev/null || true
    THREAD_URL=""
  fi
  if [[ -n "${THREAD_URL:-}" ]]; then
    printf '%s\n' "$THREAD_URL"
    exit 0
  fi
fi

# Crear thread de pruebas
navigate_url "$WID_HEX" "$BASE_URL" || true
sleep 1.0

CHATGPT_WID_HEX="$WID_HEX" "$SEND" "$MARKER_MSG" >/dev/null 2>&1 || true
sleep 1.0

new_url="$("$GET_URL" "$WID_HEX" 2>/dev/null || true)"
if ! valid_thread_url "$new_url"; then
  log "ERROR: invalid thread URL: ${new_url}"
  dump_forensics "${new_url}" "" "${WID_HEX}"
  echo "ERROR: invalid thread URL" >&2
  echo "PAID_THREAD_LOG=$LOG_PATH" >&2
  exit 5
fi

mkdir -p "$(dirname "$THREAD_FILE")"
printf '%s\n' "$new_url" > "$THREAD_FILE"
log "THREAD_CREATED=${new_url}"
printf '%s\n' "$new_url"
