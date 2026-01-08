#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# --- AUTO IPC DIR (A3.12) ---
if [[ -z "${X11_FILE_IPC_DIR:-}" ]]; then
  export X11_FILE_IPC_DIR="$ROOT/diagnostics/x11_file_ipc"
fi
# ----------------------------

REQ_ACCESS="$ROOT/scripts/x11_require_access.sh"
ENSURE="$ROOT/scripts/chatgpt_bridge_ensure.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
SEND="$ROOT/scripts/chatgpt_ui_send_x11.sh"
COPY="$ROOT/scripts/chatgpt_copy_chat_text.sh"
DISP="$ROOT/scripts/x11_dispatcher.py"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
PAID_THREAD_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_test_thread.sh"
PAID_GET_URL="$ROOT/scripts/chatgpt_paid_get_url.sh"
CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
DEFAULT_FREE_DIR="$HOME/.cache/lucy_chrome_chatgpt_free"
CHATGPT_CHROME_USER_DATA_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-${CHATGPT_BRIDGE_PROFILE_DIR:-$DEFAULT_FREE_DIR}}"
PROFILE_LOCK=0
if [[ "${CHATGPT_TARGET}" == "free" ]] && [[ -n "${CHATGPT_CHROME_USER_DATA_DIR:-}" ]]; then
  PROFILE_LOCK=1
fi
if [[ "${CHATGPT_TARGET}" == "paid" ]]; then
  CHATGPT_CHROME_USER_DATA_DIR=""
fi

PROMPT="${1:-}"
if [[ -z "${PROMPT:-}" ]]; then
  echo "ERROR: usage: $0 <prompt>" >&2
  exit 2
fi

RUN_EPOCH="$(date +%s)"
RUN_RAND="${RANDOM}"
export LUCY_ASK_TMPDIR="${LUCY_ASK_TMPDIR:-/tmp/lucy_chatgpt_ask_run_${RUN_EPOCH}_${RUN_RAND}}"
mkdir -p "$LUCY_ASK_TMPDIR"
TMP=""
TMP_MSG=""
TMPDIR_ANNOUNCED=0
SUMMARY_WRITTEN=0
META_WRITTEN=0
COMMON_WRITTEN=0
ASK_RC=1
ASK_STATUS="fail"
FAIL_REASON=""
ANSWER_LINE=""
ANSWER_EMPTY_SEEN=0
ANSWER_EMPTY_ANY=0
COPY_PRIMARY_PATH=""
COPY_SECONDARY_PATH=""
COPY_BEST_PATH=""
LAST_LINE_SEEN=""
LINE_STABLE_COUNT=0
COPY_MODE_DEFAULT="${LUCY_COPY_MODE_DEFAULT:-auto}"
COPY_MODE_FALLBACK="${LUCY_COPY_MODE_FALLBACK:-messages}"
PAID_THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-$HOME/.cache/lucy_chatgpt_paid_test_thread.url}"
if [[ ! -r "${PAID_THREAD_FILE}" ]]; then
  if [[ -r "/tmp/lucy_chatgpt_paid_test_thread.url" ]]; then
    PAID_THREAD_FILE="/tmp/lucy_chatgpt_paid_test_thread.url"
  fi
fi
PAID_THREAD_URL=""
PAID_CUR_URL=""
PAID_PID=""

now_ms() {
  local ms
  ms="$(date +%s%3N 2>/dev/null || true)"
  if ! [[ "${ms}" =~ ^[0-9]+$ ]]; then
    ms=$(( $(date +%s) * 1000 ))
  fi
  printf '%s' "${ms}"
}

get_active_wid() {
  local raw
  raw="$("$HOST_EXEC" 'xprop -root _NET_ACTIVE_WINDOW' 2>/dev/null \
    | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
  if [[ -n "${raw:-}" ]]; then
    printf '0x%08x\n' "$((raw))"
  fi
}

get_wid_title() {
  local wid="$1"
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" { \$1=\"\"; \$2=\"\"; \$3=\"\"; sub(/^ +/, \"\"); print; exit }'" 2>/dev/null || true
  fi
}

wid_exists() {
  local wid="$1"
  [[ -n "${wid:-}" ]] || return 1
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" {found=1} END{exit !found}'" >/dev/null 2>&1
    return $?
  fi
  return 0
}

get_wm_command_by_wid() {
  local wid="$1"
  if [[ -x "$HOST_EXEC" ]]; then
    local out
    out="$("$HOST_EXEC" "xprop -id ${wid} WM_COMMAND" 2>/dev/null || true)"
    if [[ "${out}" == *"not found"* ]]; then
      return 0
    fi
    printf '%s\n' "$out"
  fi
}

get_pid_by_wid() {
  local wid="$1"
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -lp | awk '\$1==\"${wid}\" {print \$3; exit}'" 2>/dev/null || true
  fi
}

get_cmdline_by_pid() {
  local pid="$1"
  [[ "${pid:-}" =~ ^[0-9]+$ ]] || return 1
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "bash -lc 'tr \"\\0\" \" \" < /proc/${pid}/cmdline 2>/dev/null'" || true
  fi
}

profile_guard_ok() {
  if [[ "${CHATGPT_TARGET}" != "free" ]]; then
    return 0
  fi
  if [[ "${PROFILE_LOCK}" -ne 1 ]]; then
    return 0
  fi
  local wid="$1"
  local cmd pid
  pid="$(get_pid_by_wid "$wid")"
  cmd="$(get_cmdline_by_pid "$pid")"
  if [[ "${cmd}" == *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]] || \
     [[ "${cmd}" == *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  cmd="$(get_wm_command_by_wid "$wid")"
  if [[ -n "${cmd:-}" ]] && ( [[ "${cmd}" == *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]] || \
    [[ "${cmd}" == *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]] ); then
    return 0
  fi
  return 1
}

resolve_wid() {
  # 1) env
  if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
    printf '%s\n' "$CHATGPT_WID_HEX"
    return 0
  fi

  # 2) selector estable (ya usa host_exec en este entorno)
  local w=""
  w="$("$GET_WID" 2>/dev/null || true)"
  if [[ -n "${w:-}" ]]; then
    printf '%s\n' "$w"
    return 0
  fi

  return 0
}

write_meta() {
  if [[ "${META_WRITTEN}" -eq 1 ]] || [[ -z "${LUCY_ASK_TMPDIR:-}" ]]; then
    return 0
  fi
  local active_wid active_title pid now
  active_wid="$(get_active_wid || true)"
  active_title="$(get_wid_title "${active_wid:-}" 2>/dev/null || true)"
  pid="$(get_pid_by_wid "${WID:-}" 2>/dev/null || true)"
  now="$(now_ms)"
  {
    echo "WID=${WID:-}"
    echo "PID=${pid:-}"
    echo "TITLE=${TITLE:-}"
    echo "TARGET=${CHATGPT_TARGET:-}"
    echo "THREAD_URL=${PAID_THREAD_URL:-}"
    echo "URL_CURRENT=${PAID_CUR_URL:-}"
    echo "COPY_MODE_DEFAULT=${COPY_MODE_DEFAULT:-}"
    echo "COPY_MODE_FALLBACK=${COPY_MODE_FALLBACK:-}"
    echo "START_MS=${START_MS:-}"
    echo "NOW_MS=${now:-}"
    echo "ACTIVE_WID=${active_wid:-}"
    echo "ACTIVE_TITLE=${active_title:-}"
  } > "$LUCY_ASK_TMPDIR/meta.txt"
  META_WRITTEN=1
}

write_common_forensics() {
  if [[ "${COMMON_WRITTEN}" -eq 1 ]] || [[ -z "${LUCY_ASK_TMPDIR:-}" ]]; then
    return 0
  fi
  local active_wid
  write_meta || true
  if [[ -n "${PAID_CUR_URL:-}" ]]; then
    printf '%s\n' "${PAID_CUR_URL}" > "$LUCY_ASK_TMPDIR/url.txt" 2>/dev/null || true
  fi
  if [[ -n "${PAID_THREAD_URL:-}" ]]; then
    printf '%s\n' "${PAID_THREAD_URL}" > "$LUCY_ASK_TMPDIR/thread_url.txt" 2>/dev/null || true
  fi
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -lp" > "$LUCY_ASK_TMPDIR/wmctrl_lp.txt" 2>/dev/null || true
  fi
  active_wid="$(get_active_wid || true)"
  if [[ -n "${active_wid:-}" ]]; then
    printf '%s\n' "${active_wid}" > "$LUCY_ASK_TMPDIR/active_wid.txt" 2>/dev/null || true
  fi
  if [[ ! -f "$LUCY_ASK_TMPDIR/copy.txt" ]]; then
    : > "$LUCY_ASK_TMPDIR/copy.txt"
  fi
  if [[ ! -f "$LUCY_ASK_TMPDIR/copy.stderr" ]]; then
    : > "$LUCY_ASK_TMPDIR/copy.stderr"
  fi
  COMMON_WRITTEN=1
}

write_summary() {
  if [[ "${SUMMARY_WRITTEN}" -eq 1 ]] || [[ -z "${LUCY_ASK_TMPDIR:-}" ]]; then
    return 0
  fi
  if [[ -z "${END_MS:-}" ]]; then
    END_MS="$(now_ms)"
  fi
  if [[ -z "${START_MS:-}" ]]; then
    START_MS="${END_MS}"
  fi
  ELAPSED_MS=$(( END_MS - START_MS ))
  if [[ "${ELAPSED_MS}" -lt 0 ]]; then
    ELAPSED_MS=0
  fi
  export START_MS END_MS ELAPSED_MS
  python3 - "$LUCY_ASK_TMPDIR/summary.json" <<'PY'
import json
import os
import sys

out = sys.argv[1]
def env(key, default=""):
    return os.environ.get(key, default)

data = {
    "token": env("TOKEN", ""),
    "wid": env("WID", ""),
    "title": env("TITLE", ""),
    "start_ms": int(env("START_MS", "0") or 0),
    "end_ms": int(env("END_MS", "0") or 0),
    "elapsed_ms": int(env("ELAPSED_MS", "0") or 0),
    "rc": int(env("ASK_RC", "1") or 1),
    "status": env("ASK_STATUS", "fail"),
    "reason": env("FAIL_REASON", ""),
    "step": "ask",
    "answer_line": env("ANSWER_LINE", ""),
    "copy_primary": env("COPY_PRIMARY_PATH", ""),
    "copy_secondary": env("COPY_SECONDARY_PATH", ""),
    "copy_best": env("COPY_BEST_PATH", ""),
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=True)
PY
  SUMMARY_WRITTEN=1
}

capture_screenshot() {
  if [[ -z "${LUCY_ASK_TMPDIR:-}" ]] || [[ -z "${WID:-}" ]]; then
    return 0
  fi
  local out err path
  out="$(mktemp /tmp/lucy_ask_shot_out.XXXX.txt)"
  err="$(mktemp /tmp/lucy_ask_shot_err.XXXX.txt)"
  python3 -u "$DISP" screenshot "$WID" >"$out" 2>"$err" || true
  path="$(sed -n 's/^PATH[[:space:]]\+\([^[:space:]]\+\).*/\1/p' "$out" | head -n 1)"
  if [[ -n "${path:-}" ]] && [[ -f "${path}" ]]; then
    cp -f "$path" "$LUCY_ASK_TMPDIR/screenshot.png" 2>/dev/null || true
    FAIL_SHOT_PATH="$path"
  fi
  rm -f "$out" "$err" 2>/dev/null || true
}

capture_failure_context() {
  capture_screenshot
  if [[ -n "${TMP:-}" ]]; then
    store_best_copy "$TMP"
  fi
  write_common_forensics || true
  write_meta
  write_summary
}

fail_exit() {
  local reason="$1"
  local rc="${2:-1}"
  FAIL_REASON="$reason"
  ASK_RC="$rc"
  ASK_STATUS="fail"
  export ASK_RC ASK_STATUS FAIL_REASON ANSWER_LINE COPY_PRIMARY_PATH COPY_SECONDARY_PATH COPY_BEST_PATH
  capture_failure_context || true
  exit "$rc"
}

announce_tmpdir() {
  if [[ "${TMPDIR_ANNOUNCED}" -ne 1 ]]; then
    printf 'LUCY_ASK_TMPDIR=%s\n' "$LUCY_ASK_TMPDIR" >&2
    TMPDIR_ANNOUNCED=1
  fi
}

cleanup() {
  if [[ -n "${FAIL_SHOT_PATH:-}" ]] && [[ -f "${FAIL_SHOT_PATH}" ]]; then
    cp -f "${FAIL_SHOT_PATH}" "$LUCY_ASK_TMPDIR/fail_screenshot.png" 2>/dev/null || true
  fi
  if [[ -n "${TMP:-}" ]]; then
    rm -f "$TMP" 2>/dev/null || true
  fi
  if [[ -n "${TMP_MSG:-}" ]]; then
    rm -f "$TMP_MSG" 2>/dev/null || true
  fi
  if [[ "${ASK_STATUS}" != "ok" ]] && [[ "${SUMMARY_WRITTEN}" -ne 1 ]]; then
    capture_failure_context || true
  else
    write_common_forensics || true
    write_meta || true
    write_summary || true
  fi
  announce_tmpdir
}

trap cleanup EXIT

# Preflight
if ! "$REQ_ACCESS" >/dev/null 2>&1; then
  echo "ERROR: no hay acceso X11 (ni IPC disponible)." >&2
  fail_exit "NO_X11" 111
fi

# Ensure bridge (no fatal)
"$ENSURE" >/dev/null 2>&1 || true

resolve_wid() {
  # 1) env
  if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
    printf '%s\n' "$CHATGPT_WID_HEX"
    return 0
  fi

  # 2) selector estable (ya usa host_exec en este entorno)
  local w=""
  w="$("$GET_WID" 2>/dev/null || true)"
  if [[ -n "${w:-}" ]]; then
    printf '%s\n' "$w"
    return 0
  fi

  return 0
}

get_wid_title() {
  local wid="$1"
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" { \$1=\"\"; \$2=\"\"; \$3=\"\"; sub(/^ +/, \"\"); print; exit }'" 2>/dev/null || true
  fi
}

WID="$(resolve_wid || true)"
if [[ -z "${WID:-}" ]]; then
  "$ENSURE" >/dev/null 2>&1 || true
  WID="$(resolve_wid || true)"
fi
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  fail_exit "NO_WID" 3
fi

TITLE="$(get_wid_title "$WID")"
if [[ "${TITLE}" == *"V.S.Code"* ]]; then
  "$ENSURE" >/dev/null 2>&1 || true
  WID="$(resolve_wid || true)"
  TITLE="$(get_wid_title "$WID")"
  if [[ "${TITLE}" == *"V.S.Code"* ]]; then
    echo "ERROR: BAD_WID_VSCODE WID=${WID} TITLE=${TITLE}" >&2
    fail_exit "BAD_WID_VSCODE" 3
  fi
fi
if ! profile_guard_ok "$WID"; then
  echo "ERROR: PROFILE_GUARD_TRIPPED WID=${WID}" >&2
  fail_exit "PROFILE_GUARD_TRIPPED" 3
fi
export CHATGPT_WID_HEX="$WID"
export WID TITLE

if [[ "${CHATGPT_TARGET}" == "paid" ]]; then
  thread_url=""
  if [[ -x "$PAID_THREAD_ENSURE" ]]; then
    thread_url="$("$PAID_THREAD_ENSURE" 2>/dev/null || true)"
  elif [[ -f "$PAID_THREAD_FILE" ]]; then
    thread_url="$(head -n 1 "$PAID_THREAD_FILE" | tr -d '\r')"
  fi
  if [[ -z "${thread_url:-}" ]]; then
    echo "ERROR: missing paid thread URL" >&2
    fail_exit "PAID_THREAD_MISSING" 3
  fi
  PAID_THREAD_URL="${thread_url}"
  cur_url=""
  if [[ -x "$PAID_GET_URL" ]]; then
    cur_url="$("$PAID_GET_URL" "$WID" 2>/dev/null || true)"
  fi
  if [[ "${cur_url}" != "${thread_url}" ]]; then
    if [[ -x "$PAID_THREAD_ENSURE" ]]; then
      "$PAID_THREAD_ENSURE" >/dev/null 2>&1 || true
    fi
    if [[ -x "$PAID_GET_URL" ]]; then
      cur_url="$("$PAID_GET_URL" "$WID" 2>/dev/null || true)"
    fi
  fi
  PAID_CUR_URL="${cur_url}"
  write_common_forensics || true
  if [[ "${cur_url}" != "${thread_url}" ]]; then
    echo "ERROR: WRONG_THREAD expected=${thread_url} got=${cur_url}" >&2
    fail_exit "WRONG_THREAD" 3
  fi
fi

TS="$(date +%s)"
RID="$(( (RANDOM % 90000) + 10000 ))"
TOKEN="${TS}_${RID}"
export TOKEN

REQ="LUCY_REQ_${TOKEN}: ${PROMPT}"
INSTR=$'Respondé SOLO con UNA línea.\nDebe empezar EXACTAMENTE con: LUCY_ANSWER_'"${TOKEN}"$': (dos puntos y un espacio)\ny en ESA MISMA LÍNEA, después de eso, poné tu respuesta.'
MSG="${REQ}"$'\n\n'"${INSTR}"

sanitize() {
  tr -d '\r' | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
}

copy_chat_to() {
  local out="$1"
  local tag="${2:-1}"
  local mode="${3:-auto}"
  local err_file=""
  : > "$out"
  if [[ -n "${LUCY_ASK_TMPDIR:-}" ]]; then
    err_file="$LUCY_ASK_TMPDIR/copy_${tag}.stderr"
  else
    err_file="/tmp/lucy_copy_${TOKEN}_${tag}.stderr"
  fi
  LUCY_COPY_MODE="$mode" timeout 25s "$COPY" >"$out" 2>"$err_file" || true
  if [[ -n "${LUCY_ASK_TMPDIR:-}" ]]; then
    cp -f "$out" "$LUCY_ASK_TMPDIR/copy_${tag}.txt" 2>/dev/null || true
    cp -f "$err_file" "$LUCY_ASK_TMPDIR/copy_${tag}.stderr" 2>/dev/null || true
  fi
}

store_best_copy() {
  local file="$1"
  if [[ -n "${LUCY_ASK_TMPDIR:-}" ]] && [[ -f "$file" ]]; then
    cp -f "$file" "$LUCY_ASK_TMPDIR/copy.txt" 2>/dev/null || true
  fi
}

chat_has() {
  local file="$1" needle="$2"
  sanitize <"$file" | grep -Fq "$needle"
}

copy_needs_retry() {
  local file="$1"
  sanitize <"$file" | grep -Fq "Tú dijiste:"
}

extract_answer_line() {
  local file="$1"
  local label="LUCY_ANSWER_${TOKEN}"
  local best=""
  local empty_seen=0
  while IFS= read -r line; do
    case "$line" in
      "${label}:"* )
        val="${line#${label}:}"
        val="${val#" "}"
        if [[ -z "${val//[[:space:]]/}" ]]; then
          empty_seen=1
          continue
        fi
        val_lc="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        if [[ "$val_lc" == *"tu respuesta"* ]] || [[ "$val_lc" == *"una sola linea"* ]] || [[ "$val_lc" == *"una sola línea"* ]]; then
          continue
        fi
        best="${label}: ${val}"
        ;;
    esac
  done < <(sanitize <"$file")
  ANSWER_EMPTY_SEEN=$empty_seen
  if [[ -n "${best:-}" ]]; then
    printf '%s\n' "$best"
  fi
}

TMP="$(mktemp /tmp/lucy_ask_${TOKEN}.XXXX.txt)"
TMP_MSG="$(mktemp /tmp/lucy_ask_${TOKEN}.msg.XXXX.txt)"

AUTO_CHAT="${LUCY_CHATGPT_AUTO_CHAT:-0}"
NEWCHAT_ATTEMPTS="${LUCY_CHATGPT_NEWCHAT_ATTEMPTS:-2}"
NEWCHAT_X="${LUCY_CHATGPT_NEWCHAT_X:-0.08}"
NEWCHAT_Y="${LUCY_CHATGPT_NEWCHAT_Y:-0.12}"
NEWCHAT_ATTEMPTED=0
NEWCHAT_OK=0

if [[ "${CHATGPT_TARGET}" == "paid" ]]; then
  AUTO_CHAT=0
  NEWCHAT_ATTEMPTS=0
fi

auto_chat_prepare() {
  if [[ "${AUTO_CHAT}" -ne 1 ]]; then
    return 0
  fi
  printf 'AUTO_CHAT=1\n' >&2
  printf 'NEWCHAT_ATTEMPTS=%s\n' "${NEWCHAT_ATTEMPTS}" >&2
  for _ in $(seq 1 "${NEWCHAT_ATTEMPTS}"); do
    NEWCHAT_ATTEMPTED=1
    python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
    python3 -u "$DISP" click "$WID" "$NEWCHAT_X" "$NEWCHAT_Y" >/dev/null 2>/dev/null || true
    sleep 0.4
  done
}

# Optional: move to a technical chat before sending.
auto_chat_prepare

# Start timer early so failure paths can compute elapsed time.
if [[ -z "${START_MS:-}" ]]; then
  START_MS="$(now_ms)"
  export START_MS
fi

# hard clear input before sending (A3.12 stability)
if [[ "${CHATGPT_CLEAR_INPUT_BEFORE_SEND:-1}" -eq 1 ]] && [[ -x "$ROOT/scripts/chatgpt_clear_input_x11.sh" ]]; then
  "$ROOT/scripts/chatgpt_clear_input_x11.sh" >/dev/null 2>/dev/null || true
fi


# 1) SEND + verificar que el REQ aparece
SENT_OK=0
for attempt in 1 2 3; do
  "$SEND" "$MSG" >/dev/null 2>/dev/null || true
  sleep 0.9
  copy_chat_to "$TMP"
  if chat_has "$TMP" "LUCY_REQ_${TOKEN}:"; then
    SENT_OK=1
    break
  fi
done

if [[ "$SENT_OK" -ne 1 ]]; then
  if [[ "${AUTO_CHAT}" -eq 1 ]]; then
    printf 'NEWCHAT_OK=0\n' >&2
  fi
  echo "ERROR: el ASK no llegó a publicarse en el chat (no vi LUCY_REQ_${TOKEN}:)." >&2
  fail_exit "SEND_NOT_PUBLISHED" 4
fi
if [[ "${AUTO_CHAT}" -eq 1 ]]; then
  if [[ "${SENT_OK}" -eq 1 ]] && [[ "${NEWCHAT_ATTEMPTED}" -eq 1 ]]; then
    NEWCHAT_OK=1
  fi
  printf 'NEWCHAT_OK=%s\n' "${NEWCHAT_OK}" >&2
fi

# 2) Esperar respuesta
TIMEOUT_SEC="${CHATGPT_ASK_TIMEOUT_SEC:-90}"
POLL_SEC="${POLL_SEC:-2}"
STALL_POLLS="${STALL_POLLS:-12}"
MAX_POLLS=$(( TIMEOUT_SEC / POLL_SEC ))
if [[ "$MAX_POLLS" -lt 5 ]]; then MAX_POLLS=5; fi

# --- A3_12_WATCHDOG ---
# Watchdog escalonado con trazas (NUDGE_1 -> NUDGE_2 -> RELOAD -> RESEND).
NUDGE_AT="${CHATGPT_ASK_NUDGE_AT:-18}"      # ~36s si POLL_SEC=2 (fallback TIMEOUT)
# RELOAD_AT queda como fallback externo si se requiere en el futuro
RELOAD_AT="${CHATGPT_ASK_RELOAD_AT:-35}"    # ~70s si POLL_SEC=2
WATCHDOG_ACTIVE=0
WATCHDOG_REASON=""
WATCHDOG_LAST_STEP=""
WATCHDOG_WAIT=0

# --- A3_12_RESEND_AFTER_RELOAD ---
# Si el backend web queda colgado (intermitente), tras reload re-enviamos el mismo MSG y seguimos esperando.
RESEND_AFTER_RELOAD="${CHATGPT_ASK_RESEND_AFTER_RELOAD:-1}"
# --- /A3_12_RESEND_AFTER_RELOAD ---

nudge_input() {
  # Best-effort: no debe matar el ask si falla
  python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
  # click en zona input (abajo-centro)
  local nx ny
  nx="${CHATGPT_INPUT_CLICK_X:-0.55}"
  ny="${CHATGPT_INPUT_CLICK_Y:-0.95}"
  python3 -u "$DISP" click "$WID" "$nx" "$ny" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "Escape" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "End" >/dev/null 2>/dev/null || true
  sleep 0.3
}

nudge_scroll() {
  python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "Page_Down" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "Page_Up" >/dev/null 2>/dev/null || true
  sleep 0.3
}

reload_ui() {
  # Ctrl+R (si la pestaña quedó colgada, esto suele destrabar)
  python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "ctrl+r" >/dev/null 2>/dev/null || true
  sleep 2.0
}

resend_msg() {
  if [[ "${RESEND_AFTER_RELOAD:-1}" -eq 1 ]]; then
    "$SEND" "$MSG" >/dev/null 2>/dev/null || true
    sleep 0.9
  fi
}
# --- /A3_12_WATCHDOG ---

i=0
stall_count=0
stall_start_ms=0
prev_copy_bytes=0
prev_copy_sha=""
prev_shot_sha=""

hash_file() {
  local f="$1"
  if command -v sha1sum >/dev/null 2>&1; then
    sha1sum "$f" | awk '{print $1}'
    return 0
  fi
  cksum "$f" | awk '{print $1}'
}

START_MS="$(now_ms)"
export START_MS

watchdog_t_ms() {
  local now
  now="$(now_ms)"
  printf '%s' "$(( now - START_MS ))"
}

watchdog_step() {
  local step="$1"
  printf 'WATCHDOG_STEP=%s t_ms=%s\n' "$step" "$(watchdog_t_ms)" >&2
  case "$step" in
    NUDGE_1)
      nudge_input
      WATCHDOG_LAST_STEP="NUDGE_1"
      WATCHDOG_WAIT=1
      ;;
    NUDGE_2)
      nudge_scroll
      WATCHDOG_LAST_STEP="NUDGE_2"
      WATCHDOG_WAIT=1
      ;;
    RELOAD)
      reload_ui
      WATCHDOG_LAST_STEP="RELOAD"
      WATCHDOG_WAIT=0
      ;;
    RESEND)
      resend_msg
      WATCHDOG_LAST_STEP="RESEND"
      WATCHDOG_ACTIVE=0
      ;;
  esac
}

watchdog_start() {
  local reason="$1"
  if [[ "${WATCHDOG_ACTIVE}" -eq 1 ]]; then
    return 0
  fi
  WATCHDOG_ACTIVE=1
  WATCHDOG_REASON="$reason"
  printf 'WATCHDOG_REASON=%s t_ms=%s\n' "$reason" "$(watchdog_t_ms)" >&2
  watchdog_step "NUDGE_1"
}

for _ in $(seq 1 "$MAX_POLLS"); do
  i=$((i+1))
  if ! wid_exists "$WID"; then
    echo "ERROR: WID desaparecido durante ask WID=${WID}" >&2
    fail_exit "WID_MISSING_DURING_ASK" 3
  fi
  copy_chat_to "$TMP" "1" "$COPY_MODE_DEFAULT"
  COPY_PRIMARY_PATH="$TMP"
  if [[ -n "${LUCY_ASK_TMPDIR:-}" ]]; then
    COPY_PRIMARY_PATH="$LUCY_ASK_TMPDIR/copy_1.txt"
  fi
  copy_best="$TMP"
  line="$(extract_answer_line "$TMP")"
  if [[ "${ANSWER_EMPTY_SEEN}" -eq 1 ]]; then
    ANSWER_EMPTY_ANY=1
  fi

  if [[ -z "${line:-}" ]] && copy_needs_retry "$TMP"; then
    copy_chat_to "$TMP_MSG" "2" "$COPY_MODE_FALLBACK"
    COPY_SECONDARY_PATH="$TMP_MSG"
    if [[ -n "${LUCY_ASK_TMPDIR:-}" ]]; then
      COPY_SECONDARY_PATH="$LUCY_ASK_TMPDIR/copy_2.txt"
    fi
    alt_line="$(extract_answer_line "$TMP_MSG")"
    if [[ "${ANSWER_EMPTY_SEEN}" -eq 1 ]]; then
      ANSWER_EMPTY_ANY=1
    fi
    if [[ -n "${alt_line:-}" ]]; then
      line="$alt_line"
      copy_best="$TMP_MSG"
    else
      bytes1="$(wc -c < "$TMP" 2>/dev/null || echo 0)"
      bytes2="$(wc -c < "$TMP_MSG" 2>/dev/null || echo 0)"
      if [[ "${bytes2}" -gt "${bytes1}" ]]; then
        copy_best="$TMP_MSG"
      fi
    fi
  fi

  store_best_copy "$copy_best"
  if [[ -n "${LUCY_ASK_TMPDIR:-}" ]]; then
    COPY_BEST_PATH="$LUCY_ASK_TMPDIR/copy.txt"
  else
    COPY_BEST_PATH="$copy_best"
  fi
  copy_bytes="$(wc -c < "$copy_best" 2>/dev/null || echo 0)"
  copy_sha="NA"
  if [[ -f "$copy_best" ]]; then
    copy_sha="$(hash_file "$copy_best" 2>/dev/null || echo NA)"
  fi
  shot_sha="NA"
  progress=0
  if [[ -z "${prev_copy_sha}" ]]; then
    progress=1
  elif [[ "${copy_sha}" != "${prev_copy_sha}" ]]; then
    progress=1
  elif [[ $(( copy_bytes - prev_copy_bytes )) -ge 20 ]]; then
    progress=1
  elif [[ "${shot_sha}" != "NA" ]] && [[ -n "${prev_shot_sha}" ]] && [[ "${shot_sha}" != "${prev_shot_sha}" ]]; then
    progress=1
  fi

  poll_ms="$(now_ms)"
  if [[ "${progress}" -eq 1 ]]; then
    stall_count=0
    stall_start_ms=0
  else
    stall_count=$((stall_count + 1))
    if [[ "${stall_start_ms}" -eq 0 ]]; then
      stall_start_ms="${poll_ms}"
    fi
  fi

  printf 'POLL i=%s copy_bytes=%s copy_sha=%s shot_sha=%s progress=%s stall=%s\n' \
    "$i" "$copy_bytes" "$copy_sha" "$shot_sha" "$progress" "$stall_count" >&2

  if [[ "${WATCHDOG_ACTIVE}" -eq 1 ]] && [[ "${progress}" -eq 1 ]] && \
     [[ "${WATCHDOG_LAST_STEP}" == "NUDGE_1" || "${WATCHDOG_LAST_STEP}" == "NUDGE_2" ]]; then
    printf 'WATCHDOG_ABORTED step=%s reason=PROGRESS_RETURNED\n' "$WATCHDOG_LAST_STEP" >&2
    WATCHDOG_ACTIVE=0
    WATCHDOG_REASON=""
    WATCHDOG_LAST_STEP=""
    WATCHDOG_WAIT=0
  fi

  watchdog_skip_decrement=0
  stall_elapsed_ms=0
  if [[ "${stall_start_ms}" -gt 0 ]]; then
    stall_elapsed_ms=$(( poll_ms - stall_start_ms ))
  fi
  stall_ms_threshold=$(( STALL_POLLS * POLL_SEC * 1000 ))
  if [[ "${stall_count}" -ge "${STALL_POLLS}" ]] || [[ "${stall_elapsed_ms}" -ge "${stall_ms_threshold}" ]]; then
    printf 'STALL_DETECTED polls=%s seconds=%s\n' "$stall_count" "$((stall_count * POLL_SEC))" >&2
    if [[ "${WATCHDOG_ACTIVE}" -ne 1 ]]; then
      watchdog_start "STALL"
      watchdog_skip_decrement=1
    fi
  fi

  if [[ "${WATCHDOG_ACTIVE}" -ne 1 ]] && [[ "$i" -eq "$NUDGE_AT" ]] && [[ "${progress}" -eq 0 ]]; then
    watchdog_start "TIMEOUT"
    watchdog_skip_decrement=1
  fi

  if [[ "${WATCHDOG_ACTIVE}" -eq 1 ]]; then
    if [[ "${WATCHDOG_WAIT}" -gt 0 ]] && [[ "${watchdog_skip_decrement}" -eq 0 ]]; then
      WATCHDOG_WAIT=$((WATCHDOG_WAIT - 1))
    fi
    if [[ "${WATCHDOG_WAIT}" -eq 0 ]] && [[ "${progress}" -eq 0 ]]; then
      if [[ "${WATCHDOG_LAST_STEP}" == "NUDGE_1" ]]; then
        watchdog_step "NUDGE_2"
      elif [[ "${WATCHDOG_LAST_STEP}" == "NUDGE_2" ]]; then
        watchdog_step "RELOAD"
        watchdog_step "RESEND"
      fi
    fi
  fi

  prev_copy_bytes="${copy_bytes}"
  prev_copy_sha="${copy_sha}"
  prev_shot_sha="${shot_sha}"

  if [[ -n "${line:-}" ]]; then
    if [[ "$line" == "$LAST_LINE_SEEN" ]]; then
      LINE_STABLE_COUNT=$((LINE_STABLE_COUNT + 1))
    else
      LAST_LINE_SEEN="$line"
      LINE_STABLE_COUNT=0
    fi
    if [[ "${LINE_STABLE_COUNT}" -ge 1 ]]; then
      ANSWER_LINE="$line"
      ASK_RC=0
      ASK_STATUS="ok"
      END_MS="$(now_ms)"
      ELAPSED_MS=$(( END_MS - START_MS ))
      if [[ "${ELAPSED_MS}" -lt 0 ]]; then
        ELAPSED_MS=0
      fi
      export ASK_RC ASK_STATUS ANSWER_LINE END_MS ELAPSED_MS COPY_PRIMARY_PATH COPY_SECONDARY_PATH COPY_BEST_PATH FAIL_REASON
      write_meta || true
      write_summary || true
      printf '%s\n' "$line"
      exit 0
    fi
  else
    LAST_LINE_SEEN=""
    LINE_STABLE_COUNT=0
  fi
  sleep "$POLL_SEC"
done

if [[ "${ANSWER_EMPTY_ANY}" -eq 1 ]]; then
  FAIL_REASON="ANSWER_EMPTY"
else
  FAIL_REASON="TIMEOUT"
fi
ASK_RC=1
ASK_STATUS="fail"
END_MS="$(now_ms)"
ELAPSED_MS=$(( END_MS - START_MS ))
if [[ "${ELAPSED_MS}" -lt 0 ]]; then
  ELAPSED_MS=0
fi
export ASK_RC ASK_STATUS ANSWER_LINE END_MS ELAPSED_MS COPY_PRIMARY_PATH COPY_SECONDARY_PATH COPY_BEST_PATH FAIL_REASON
capture_failure_context || true
echo "ERROR: timeout esperando LUCY_ANSWER_${TOKEN}:" >&2
exit 1
