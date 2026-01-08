#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"
TARGET="${CHATGPT_TARGET:-free}"
PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}"
export CHATGPT_TARGET="${TARGET}"
export CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
export CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"

check_wid() {
  local wid="$1"
  [[ "${wid}" =~ ^0x[0-9a-fA-F]+$ ]]
}

get_title() {
  local wid="$1"
  "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" { \$1=\"\"; \$2=\"\"; \$3=\"\"; sub(/^ +/, \"\"); print; exit }'" 2>/dev/null || true
}

get_wmctrl_lp() {
  "$HOST_EXEC" 'wmctrl -lp' 2>/dev/null || true
}

get_pid_by_wid() {
  local wid="$1"
  get_wmctrl_lp | awk -v w="$wid" '$1==w {print $3; exit}'
}

get_cmdline_by_pid() {
  local pid="$1"
  [[ "${pid:-}" =~ ^[0-9]+$ ]] || return 1
  "$HOST_EXEC" "bash -lc 'tr \"\\0\" \" \" < /proc/${pid}/cmdline 2>/dev/null'" || true
}

get_wm_command_by_wid() {
  local wid="$1"
  local out
  out="$("$HOST_EXEC" "xprop -id ${wid} WM_COMMAND" 2>/dev/null || true)"
  if [[ "${out}" == *"not found"* ]]; then
    return 0
  fi
  printf '%s\n' "$out"
}

cmdline_is_chrome() {
  local cmd="$1"
  [[ -n "${cmd:-}" ]] || return 1
  local cmd_lc
  cmd_lc="${cmd,,}"
  if [[ "$cmd_lc" == *"google-chrome"* ]] || [[ "$cmd_lc" == *"chromium"* ]] || [[ "$cmd_lc" == *"chrome/chrome"* ]]; then
    return 0
  fi
  return 1
}

cmdline_has_user_data() {
  local cmd="$1"
  local dir="$2"
  [[ -n "${cmd:-}" ]] || return 1
  if [[ "${cmd}" == *"--user-data-dir=${dir}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${dir}"* ]]; then
    return 0
  fi
  return 1
}

if [[ "${TARGET}" != "free" ]]; then
  WID1="$($GET_WID)"
  if ! check_wid "${WID1}"; then
    echo "ERROR: invalid WID format: ${WID1}" >&2
    exit 1
  fi
  TITLE1="$(get_title "${WID1}")"
  if [[ "${TARGET}" == "paid" ]]; then
    if [[ "${TITLE1}" != *"ChatGPT"* ]]; then
      echo "ERROR: paid title does not include ChatGPT: ${TITLE1}" >&2
      exit 1
    fi
    pid="$(get_pid_by_wid "${WID1}")"
    cmd="$(get_cmdline_by_pid "${pid}")"
    if cmdline_has_user_data "${cmd}" "$PROFILE_DIR"; then
      echo "ERROR: paid WID is in free profile: ${WID1}" >&2
      exit 1
    fi
  else
    if [[ "${TITLE1}" != *"LUCY Dummy Chat"* ]]; then
      echo "ERROR: dummy title mismatch: ${TITLE1}" >&2
      exit 1
    fi
  fi
  echo "VERIFY_CHATGPT_GET_WID_OK"
  exit 0
fi

wm_command_has_user_data() {
  local wid="$1"
  local dir="$2"
  local cmd
  cmd="$(get_wm_command_by_wid "$wid")"
  if [[ -z "${cmd:-}" ]]; then
    echo "WARN: WM_COMMAND missing for ${wid}" >&2
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir=${dir}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${dir}"* ]]; then
    return 0
  fi
  return 1
}

list_chrome_wids() {
  get_wmctrl_lp | awk '{print $1 "\t" $3}' | while IFS=$'\t' read -r wid pid; do
    [[ -z "${wid:-}" ]] && continue
    cmd="$(get_cmdline_by_pid "$pid")"
    if cmdline_is_chrome "$cmd"; then
      printf '%s\n' "$wid"
    fi
  done
}

find_new_wid() {
  local before="$1"
  local after="$2"
  comm -13 <(printf '%s\n' "$before" | sort) <(printf '%s\n' "$after" | sort) | tail -n 1
}

wid_is_chrome() {
  local wid="$1"
  local pid cmd
  pid="$(get_pid_by_wid "$wid")"
  cmd="$(get_cmdline_by_pid "$pid")"
  cmdline_is_chrome "$cmd"
}

find_wid_by_user_data_dir() {
  local dir="$1"
  get_wmctrl_lp | while IFS= read -r line; do
    wid="$(awk '{print $1}' <<< "$line")"
    pid="$(awk '{print $3}' <<< "$line")"
    [[ -z "${wid:-}" ]] && continue
    cmd="$(get_cmdline_by_pid "$pid")"
    if cmdline_has_user_data "$cmd" "$dir"; then
      printf '%s\n' "$wid"
      return 0
    fi
  done
  return 1
}

WID1="$($GET_WID)"
if ! check_wid "${WID1}"; then
  echo "ERROR: invalid WID format: ${WID1}" >&2
  exit 1
fi

TITLE1="$(get_title "${WID1}")"
if [[ "${TITLE1}" == *"V.S.Code"* ]]; then
  echo "ERROR: WID title contains V.S.Code: ${TITLE1}" >&2
  exit 1
fi
if ! wm_command_has_user_data "${WID1}" "$PROFILE_DIR"; then
  echo "ERROR: WID not in profile dir (WM_COMMAND): ${WID1}" >&2
  exit 1
fi

export CHATGPT_GET_WID_NOOPEN=1

for i in 1 2 3 4 5 6 7 8 9 10; do
  wid="$($GET_WID)"
  if [[ "${wid}" != "${WID1}" ]]; then
    echo "ERROR: unstable WID at run ${i}: got ${wid}, expected ${WID1}" >&2
    exit 1
  fi
  title="$(get_title "${wid}")"
  if [[ "${title}" == *"V.S.Code"* ]]; then
    echo "ERROR: WID title contains V.S.Code at run ${i}: ${title}" >&2
    exit 1
  fi
done

if [[ "${LUCY_SKIP_RECOVERY_TEST:-0}" -ne 1 ]]; then
  unset CHATGPT_GET_WID_NOOPEN
  unset CHATGPT_WID_PIN_ONLY
  TMP_PIN="$(mktemp /tmp/lucy_chatgpt_pin_fake.XXXX.txt)"
  RECOVER_ERR="$(mktemp /tmp/verify_chatgpt_get_wid_recover_err.XXXX.txt)"
  DISTRACTOR_DIR="$(mktemp -d /tmp/lucy_chrome_distractor.XXXX)"
  DISTRACTOR_CLASS="lucy-chatgpt-distractor"
  cleanup_pin() {
    rm -f "$TMP_PIN" 2>/dev/null || true
    rm -f "$RECOVER_ERR" 2>/dev/null || true
    if [[ -n "${distractor_wid:-}" ]]; then
      "$HOST_EXEC" "wmctrl -ic ${distractor_wid}" >/dev/null 2>&1 || true
    fi
    rm -rf "$DISTRACTOR_DIR" 2>/dev/null || true
  }
  trap cleanup_pin EXIT

  printf '0xDEADBEEF\nTITLE=Fake\n' > "$TMP_PIN"
  export CHATGPT_WID_PIN_FILE="$TMP_PIN"

  before_wids="$(list_chrome_wids)"
  if [[ ! -x "$CHROME_OPEN" ]]; then
    echo "ERROR: missing chatgpt_chrome_open.sh" >&2
    exit 1
  fi
  CHATGPT_CHROME_USER_DATA_DIR="${DISTRACTOR_DIR}" \
    CHATGPT_BRIDGE_CLASS="${DISTRACTOR_CLASS}" \
    CHATGPT_OPEN_URL="https://chatgpt.com" \
    "$CHROME_OPEN" >/dev/null 2>&1 || true
  distractor_wid=""
  for _ in $(seq 1 15); do
    sleep 1
    distractor_wid="$(find_wid_by_user_data_dir "$DISTRACTOR_DIR" || true)"
    if [[ -n "${distractor_wid:-}" ]]; then
      break
    fi
    after_wids="$(list_chrome_wids)"
    distractor_wid="$(find_new_wid "$before_wids" "$after_wids")"
    [[ -n "${distractor_wid:-}" ]] && break
  done
  if [[ -z "${distractor_wid:-}" ]]; then
    echo "ERROR: failed to detect distractor Chrome window" >&2
    exit 1
  fi

  RECOVER_WID="$($GET_WID 2> "$RECOVER_ERR" || true)"
  cat "$RECOVER_ERR" >&2 || true

  if ! check_wid "${RECOVER_WID}"; then
    echo "ERROR: invalid recovered WID format: ${RECOVER_WID}" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi
  if ! grep -q 'PIN_INVALID=1' "$RECOVER_ERR"; then
    echo "ERROR: missing PIN_INVALID=1 in stderr" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi
  if ! grep -q 'PIN_RECOVERED=1' "$RECOVER_ERR"; then
    echo "ERROR: missing PIN_RECOVERED=1 in stderr" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi

  if [[ "${RECOVER_WID}" == "${distractor_wid}" ]]; then
    echo "ERROR: recovered WID matches distractor: ${RECOVER_WID}" >&2
    exit 1
  fi
  if ! wid_is_chrome "${RECOVER_WID}"; then
    echo "ERROR: recovered WID is not chrome: ${RECOVER_WID}" >&2
    exit 1
  fi
  rec_pid="$(get_pid_by_wid "$RECOVER_WID")"
  rec_cmd="$(get_cmdline_by_pid "$rec_pid")"
  if ! cmdline_has_user_data "$rec_cmd" "$PROFILE_DIR"; then
    echo "ERROR: recovered WID not in profile dir (cmdline): ${RECOVER_WID}" >&2
    exit 1
  fi
  if ! wm_command_has_user_data "$RECOVER_WID" "$PROFILE_DIR"; then
    echo "ERROR: recovered WID not in profile dir: ${RECOVER_WID}" >&2
    exit 1
  fi

  TITLE_RECOVER="$(get_title "${RECOVER_WID}")"
  if [[ "${TITLE_RECOVER}" == *"V.S.Code"* ]]; then
    echo "ERROR: recovered WID title contains V.S.Code: ${TITLE_RECOVER}" >&2
    exit 1
  fi
fi

find_google_chrome_usage() {
  if command -v rg >/dev/null 2>&1; then
    rg -n "google-chrome" "$ROOT/scripts"
    return 0
  fi
  grep -R -n "google-chrome" "$ROOT/scripts" || true
}

if find_google_chrome_usage | grep -v "chatgpt_chrome_open.sh" | grep -v "chatgpt_get_wid.sh" | grep -v "verify_chatgpt_get_wid.sh" | grep -v "x11_dispatcher.py" >/dev/null; then
  echo "ERROR: found google-chrome usage outside chatgpt_chrome_open.sh" >&2
  find_google_chrome_usage | grep -v "chatgpt_chrome_open.sh" | grep -v "chatgpt_get_wid.sh" | grep -v "verify_chatgpt_get_wid.sh" | grep -v "x11_dispatcher.py" >&2 || true
  exit 1
fi

echo "VERIFY_CHATGPT_GET_WID_OK"
