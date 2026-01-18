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

HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
PAID_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_chatgpt.sh"
THREAD_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_test_thread.sh"
GET_URL="$ROOT/scripts/chatgpt_paid_get_url.sh"
PIN="$ROOT/scripts/chatgpt_pin_wid.sh"
UNPIN="$ROOT/scripts/chatgpt_unpin_wid.sh"
RESOLVE_BY_URL="$ROOT/scripts/chatgpt_resolve_wid_by_url.sh"

export CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
if [[ "${CHATGPT_TARGET}" != "paid" ]]; then
  echo "ERROR: chatgpt_paid_preflight_one_shot requiere CHATGPT_TARGET=paid" >&2
  exit 2
fi

export CHATGPT_ALLOW_ACTIVE_WINDOW="${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}"
export CHATGPT_WID_PIN_ONLY="${CHATGPT_WID_PIN_ONLY:-1}"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"

LOG_PATH="${CHATGPT_PAID_PREFLIGHT_LOG:-/tmp/paid_preflight_one_shot.log}"
PIN_FILE="${CHATGPT_WID_PIN_FILE_PAID:-$ROOT/diagnostics/pins/chatgpt_diego.wid}"
FORENSICS_DIR="/tmp/lucy_chatgpt_bridge/$(date +%F)/PREFLIGHT_$(date +%s)_$RANDOM"
mkdir -p "$(dirname "$LOG_PATH")" "$FORENSICS_DIR"
: >"$LOG_PATH"

log() {
  printf '%s\n' "$*" >>"$LOG_PATH"
}

ensure_pin_file() {
  local f="$1"
  local dir
  dir="$(dirname "$f")"
  mkdir -p "$dir" 2>/dev/null || true
  if [[ -e "$f" ]]; then
    dd if=/dev/null of="$f" 2>/dev/null || return 1
  else
    local tmp
    tmp="$(mktemp "$dir/.pinwrite.XXXX" 2>/dev/null)" || return 1
    rm -f "$tmp" 2>/dev/null || true
  fi
  return 0
}
if ! ensure_pin_file "$PIN_FILE"; then
  PIN_FILE="/tmp/lucy_chatgpt_wid_pin_paid"
  mkdir -p "$(dirname "$PIN_FILE")" 2>/dev/null || true
  log "WARN: PIN_FILE not writable, using ${PIN_FILE}"
fi
export CHATGPT_WID_PIN_FILE="$PIN_FILE"

get_pid_by_wid() {
  "$HOST_EXEC" "wmctrl -lp | awk '\$1==\"$1\" {print \$3; exit}'" 2>/dev/null || true
}

write_forensics() {
  local wid="$1" pid="$2" thread_url="$3" cur_url="$4"
  local active_wid
  printf '%s\n' "$thread_url" > "$FORENSICS_DIR/thread_url.txt" 2>/dev/null || true
  printf '%s\n' "$cur_url" > "$FORENSICS_DIR/url.txt" 2>/dev/null || true
  "$HOST_EXEC" "wmctrl -lp" > "$FORENSICS_DIR/wmctrl_lp.txt" 2>/dev/null || true
  if [[ "${CHATGPT_ALLOW_ACTIVE_WINDOW}" -eq 1 ]]; then
    active_wid="$("$HOST_EXEC" "xprop -root _NET_ACTIVE_WINDOW" 2>/dev/null | sed -n 's/.*\\(0x[0-9a-fA-F]\\+\\).*/\\1/p' | head -n 1)"
  fi
  printf '%s\n' "${active_wid:-}" > "$FORENSICS_DIR/active_wid.txt" 2>/dev/null || true
  {
    echo "TARGET=paid"
    echo "WID=${wid:-}"
    echo "PID=${pid:-}"
    echo "THREAD_URL=${thread_url:-}"
    echo "URL_CURRENT=${cur_url:-}"
    echo "START_MS=$(date +%s%3N 2>/dev/null || true)"
  } > "$FORENSICS_DIR/meta.txt" 2>/dev/null || true
}

fail_exit() {
  local msg="$1"
  log "ERROR: ${msg}"
  echo "ERROR: ${msg}" >&2
  echo "PAID_PREFLIGHT_LOG=$LOG_PATH" >&2
  echo "FORENSICS_DIR=$FORENSICS_DIR" >&2
  exit 1
}

PAID_WID=""
PAID_PID=""
if [[ "${CHATGPT_WID_PIN_ONLY}" -eq 1 ]]; then
  if [[ ! -s "${PIN_FILE}" ]]; then
    set +e
    CHATGPT_WID_PIN_FILE="$PIN_FILE" "$RESOLVE_BY_URL" 12 9 >/dev/null 2>&1
    resolve_rc=$?
    set -e
    if [[ "$resolve_rc" -ne 0 ]]; then
      write_forensics "" "" "" ""
      fail_exit "resolve by url failed"
    fi
  fi
  PAID_WID="$(head -n 1 "$PIN_FILE" 2>/dev/null | sed -n 's/.*\\(0x[0-9a-fA-F]\\+\\).*/\\1/p' | head -n 1)"
  if [[ -n "${PAID_WID:-}" ]]; then
    PAID_PID="$(get_pid_by_wid "$PAID_WID")"
  fi
fi

ensure_out=""
if [[ -z "${PAID_WID:-}" ]] || [[ -z "${PAID_PID:-}" ]]; then
  ensure_out="$("$PAID_ENSURE" 2>>"$LOG_PATH" || true)"
  PAID_WID="$(printf '%s\n' "$ensure_out" | awk -F= '/PAID_CHATGPT_WID=/{print $2}' | tail -n 1)"
  PAID_PID="$(printf '%s\n' "$ensure_out" | awk -F= '/PAID_CHATGPT_PID=/{print $2}' | tail -n 1)"
fi
if [[ -z "${PAID_WID:-}" ]] || [[ -z "${PAID_PID:-}" ]]; then
  write_forensics "" "" "" ""
  fail_exit "paid ensure failed"
fi

THREAD_URL="$(PAID_CHATGPT_WID="$PAID_WID" PAID_CHATGPT_PID="$PAID_PID" CHATGPT_PAID_ENSURE_CALLER=1 "$THREAD_ENSURE" 2>>"$LOG_PATH" || true)"
if [[ -z "${THREAD_URL:-}" ]]; then
  write_forensics "$PAID_WID" "$PAID_PID" "" ""
  fail_exit "thread ensure failed"
fi

CHATGPT_TARGET=paid CHATGPT_WID_HEX="$PAID_WID" "$UNPIN" >/dev/null 2>&1 || true
pin_out="$(CHATGPT_TARGET=paid CHATGPT_WID_HEX="$PAID_WID" "$PIN" 2>&1)" || pin_rc=$?
log "$pin_out"
if [[ "${pin_rc:-0}" -ne 0 ]]; then
  write_forensics "$PAID_WID" "$PAID_PID" "$THREAD_URL" ""
  fail_exit "pin failed"
fi
pin_file_used="$(printf '%s\n' "$pin_out" | awk -F= '/PIN_FILE=/{print $2; exit}' | awk '{print $1}' | tr -d '\r')"
if [[ -n "${pin_file_used:-}" ]]; then
  PIN_FILE="$pin_file_used"
  export CHATGPT_WID_PIN_FILE="$PIN_FILE"
fi
PIN_WID="$(head -n 1 "$PIN_FILE" 2>/dev/null | sed -n 's/.*\\(0x[0-9a-fA-F]\\+\\).*/\\1/p' | head -n 1)"
if [[ -z "${PIN_WID:-}" ]]; then
  PIN_WID="$(printf '%s\n' "$pin_out" | awk -F= '/PINNED_WID=/{print $2; exit}' | tr -d '\r')"
  if [[ -n "${PIN_WID:-}" ]]; then
    {
      echo "$PIN_WID"
      echo "TITLE=ChatGPT - Google Chrome"
    } > "$PIN_FILE" 2>/dev/null || true
  fi
fi
if [[ -z "${PIN_WID:-}" ]]; then
  write_forensics "$PAID_WID" "$PAID_PID" "$THREAD_URL" ""
  fail_exit "pin file missing or empty"
fi

wm_out="$("$HOST_EXEC" "wmctrl -lp" 2>/dev/null || true)"
PIN_PID="$(printf '%s\n' "$wm_out" | awk -v wid="$PIN_WID" '$1==wid {print $3; exit}')"
if [[ "${PIN_PID}" != "${PAID_PID}" ]]; then
  write_forensics "$PIN_WID" "$PIN_PID" "$THREAD_URL" ""
  fail_exit "pin pid mismatch expected=${PAID_PID} got=${PIN_PID}"
fi

match_ok=0
for _ in 1 2 3; do
  CUR_URL="$("$GET_URL" "$PIN_WID" 2>>"$LOG_PATH" || true)"
  if [[ "${CUR_URL}" == "${THREAD_URL}" ]]; then
    match_ok=1
    break
  fi
  THREAD_URL="$(PAID_CHATGPT_WID="$PAID_WID" PAID_CHATGPT_PID="$PAID_PID" CHATGPT_PAID_ENSURE_CALLER=1 "$THREAD_ENSURE" 2>>"$LOG_PATH" || true)"
  sleep 0.4
done
write_forensics "$PIN_WID" "$PIN_PID" "$THREAD_URL" "$CUR_URL"
if [[ "${match_ok}" -ne 1 ]]; then
  fail_exit "thread url mismatch"
fi

log "PAID_PREFLIGHT_OK wid=${PIN_WID} pid=${PIN_PID}"
echo "PAID_PREFLIGHT_OK WID=${PIN_WID} PID=${PIN_PID}"
