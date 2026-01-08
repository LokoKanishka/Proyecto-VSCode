#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"
ASK="$ROOT/scripts/chatgpt_ui_ask_x11.sh"

PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}"
export CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
export CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"

DUMMY_FILE="$ROOT/diagnostics/ui_dummy_chat.html"
if [[ ! -f "$DUMMY_FILE" ]]; then
  echo "ERROR: missing dummy file: ${DUMMY_FILE}" >&2
  exit 1
fi

if [[ ! -x "$CHROME_OPEN" ]]; then
  echo "ERROR: missing chatgpt_chrome_open.sh" >&2
  exit 1
fi

get_wmctrl_lp() {
  "$HOST_EXEC" 'wmctrl -lp' 2>/dev/null || true
}

get_cmdline_by_pid() {
  local pid="$1"
  [[ "${pid:-}" =~ ^[0-9]+$ ]] || return 1
  "$HOST_EXEC" "bash -lc 'tr \"\\0\" \" \" < /proc/${pid}/cmdline 2>/dev/null'" || true
}

get_wm_command_by_wid() {
  local wid="$1"
  "$HOST_EXEC" "xprop -id ${wid} WM_COMMAND" 2>/dev/null || true
}

cmdline_has_user_data() {
  local cmd="$1"
  if [[ "${cmd}" == *"--user-data-dir=${PROFILE_DIR}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${PROFILE_DIR}"* ]]; then
    return 0
  fi
  return 1
}

wm_command_has_user_data() {
  local wid="$1"
  local cmd
  cmd="$(get_wm_command_by_wid "$wid")"
  [[ -n "${cmd:-}" ]] || return 1
  if [[ "${cmd}" == *"--user-data-dir=${PROFILE_DIR}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${PROFILE_DIR}"* ]]; then
    return 0
  fi
  return 1
}

choose_latest_wid() {
  local max_dec=-1
  local max_wid=""
  local wid dec
  while IFS=$'\t' read -r wid _; do
    [[ -z "${wid:-}" ]] && continue
    dec="$(printf "%d" "$wid" 2>/dev/null || echo -1)"
    if [[ "$dec" -gt "$max_dec" ]]; then
      max_dec="$dec"
      max_wid="$wid"
    fi
  done
  [[ -n "${max_wid:-}" ]] && printf '%s\n' "$max_wid"
}

URL="file://${DUMMY_FILE}"
CHATGPT_OPEN_URL="$URL" \
  CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR" \
  CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS}" \
  "$CHROME_OPEN" >/dev/null 2>&1 || true

dummy_wid=""
for _ in $(seq 1 20); do
  sleep 0.5
  candidates="$(get_wmctrl_lp | awk -v t="LUCY Dummy Chat" '
    {
      wid=$1; pid=$3; title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      if (index(title, t) > 0) {
        printf "%s\t%s\n", wid, pid
      }
    }
  ')"
  if [[ -n "${candidates:-}" ]]; then
    filtered=""
    while IFS=$'\t' read -r wid pid; do
      cmd="$(get_cmdline_by_pid "$pid")"
      if ! cmdline_has_user_data "$cmd"; then
        continue
      fi
      if ! wm_command_has_user_data "$wid"; then
        continue
      fi
      filtered+="${wid}\t${pid}\n"
    done <<< "$candidates"
    dummy_wid="$(printf '%b' "$filtered" | choose_latest_wid || true)"
    [[ -n "${dummy_wid:-}" ]] && break
  fi
done

if [[ -z "${dummy_wid:-}" ]]; then
  echo "ERROR: failed to detect dummy window" >&2
  exit 1
fi

cleanup() {
  "$HOST_EXEC" "wmctrl -ic ${dummy_wid}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

CHATGPT_WID_HEX="$dummy_wid" \
  CHATGPT_CLEAR_INPUT_BEFORE_SEND=0 \
  LUCY_CHATGPT_AUTO_CHAT=0 \
  CHATGPT_GET_WID_NOOPEN=1 \
  "$ASK" "dummy" >/tmp/verify_ui_dummy_pipe.out 2>/tmp/verify_ui_dummy_pipe.err

if ! grep -q "^LUCY_ANSWER_" /tmp/verify_ui_dummy_pipe.out; then
  echo "ERROR: dummy pipe did not return answer line" >&2
  cat /tmp/verify_ui_dummy_pipe.err >&2 || true
  exit 1
fi

echo "VERIFY_UI_DUMMY_PIPE_OK"
