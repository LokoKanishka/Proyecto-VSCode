#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
CHATGPT_CHROME_USER_DATA_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}}"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${PROFILE_NAME}}"
export CHATGPT_WID_PIN_FILE="$PIN_FILE"
TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-ChatGPT}"
TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-V.S.Code}"
CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
PROFILE_LOCK=0
if [[ -n "${CHATGPT_CHROME_USER_DATA_DIR:-}" ]]; then
  PROFILE_LOCK=1
  printf 'PROFILE_LOCK=1 user_data_dir=%s\n' "$CHATGPT_CHROME_USER_DATA_DIR" >&2
fi

get_active_wid() {
  local raw
  raw="$("$HOST_EXEC" 'xprop -root _NET_ACTIVE_WINDOW' 2>/dev/null \
    | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
  if [[ -n "${raw:-}" ]]; then
    printf '0x%08x\n' "$((raw))"
  fi
}

get_title() {
  local wid="$1"
  local wins
  wins="$("$HOST_EXEC" 'wmctrl -l' 2>/dev/null || true)"
  awk -v w="$wid" '$1==w { $1=""; $2=""; $3=""; sub(/^ +/, ""); print; exit }' <<< "$wins"
}

get_pid_by_wid() {
  local wid="$1"
  "$HOST_EXEC" "wmctrl -lp | awk '\$1==\"${wid}\" {print \$3; exit}'" 2>/dev/null || true
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

wm_command_matches_profile() {
  if [[ "${PROFILE_LOCK}" -ne 1 ]]; then
    return 0
  fi
  local wid="$1"
  local cmd
  cmd="$(get_wm_command_by_wid "$wid")"
  [[ -n "${cmd:-}" ]] || return 1
  if [[ "${cmd}" == *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  return 1
}

wid="$(get_active_wid)"
if [[ -z "${wid:-}" ]]; then
  echo "ERROR: no active window detected" >&2
  exit 1
fi

title="$(get_title "$wid")"
if [[ -n "${TITLE_INCLUDE}" ]] && [[ "${title}" != *"${TITLE_INCLUDE}"* ]]; then
  if [[ "${PROFILE_LOCK}" -eq 1 ]]; then
    echo "WARN: title does not include ChatGPT (TITLE='${title}')" >&2
  else
    echo "ERROR: active window is not ChatGPT (TITLE='${title}')" >&2
    exit 1
  fi
fi
if [[ -n "${TITLE_EXCLUDE}" ]] && [[ "${title}" == *"${TITLE_EXCLUDE}"* ]]; then
  echo "ERROR: active window is excluded (TITLE='${title}')" >&2
  exit 1
fi

if [[ "${PROFILE_LOCK}" -eq 1 ]]; then
  pid="$(get_pid_by_wid "$wid")"
  cmd="$(get_cmdline_by_pid "$pid")"
  if [[ "${cmd}" != *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]] && \
     [[ "${cmd}" != *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    echo "ERROR: active window is not in profile lock (PID=${pid})" >&2
    exit 1
  fi
  if ! wm_command_matches_profile "$wid"; then
    echo "ERROR: active window does not match WM_COMMAND profile lock (PID=${pid})" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$PIN_FILE")"
{
  echo "$wid"
  echo "TITLE=$title"
} > "$PIN_FILE"

printf 'PINNED_WID=%s\n' "$wid"
printf 'PIN_FILE=%s TITLE=%s\n' "$PIN_FILE" "$title" >&2
