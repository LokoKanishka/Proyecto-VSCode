#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"
COPY="$ROOT/scripts/chatgpt_copy_chat_text.sh"

export CHATGPT_TARGET="dummy"
export CHATGPT_PROFILE_NAME="dummy"
PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}"
export CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
export CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"

DUMMY_FILE="$ROOT/diagnostics/ui_dummy_chat.html"
DUMMY_CLASS="lucy-dummy-bridge"
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

get_wmctrl_l() {
  "$HOST_EXEC" 'wmctrl -l' 2>/dev/null || true
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
  if [[ -z "${cmd:-}" ]]; then
    return 0
  fi
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

URL="file://${DUMMY_FILE}?t=$(date +%s%N)"
CHATGPT_OPEN_URL="$URL" \
  CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR" \
  CHATGPT_BRIDGE_CLASS="${DUMMY_CLASS}" \
  "$CHROME_OPEN" >/dev/null 2>&1 || true

dummy_wid=""
for _ in $(seq 1 20); do
  sleep 0.5
  candidates="$(get_wmctrl_l | awk -v tag="${DUMMY_CLASS}" -v title="LUCY Dummy Chat" '
    {
      wid=$1;
      t="";
      for(i=4;i<=NF;i++){ t = t (i==4 ? "" : " ") $i }
      if (tolower(t) ~ tolower(tag) || index(t, title) > 0) {
        printf "%s\n", wid
      }
    }
  ')"
  if [[ -n "${candidates:-}" ]]; then
    filtered=""
    while IFS= read -r wid; do
      [[ -z "${wid:-}" ]] && continue
      pid="$(get_wmctrl_lp | awk -v w="${wid}" '$1==w {print $3; exit}')"
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

TOKEN="$(date +%s)_$(( (RANDOM % 90000) + 10000 ))"
MSG="LUCY_REQ_${TOKEN}: dummy"

MSG_Q="$(printf '%q' "$MSG")"
"$HOST_EXEC" "bash -lc '
set -euo pipefail
WID_HEX=${dummy_wid}
WID_DEC=\$(printf \"%d\" \"\$WID_HEX\")
wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true
xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true
sleep 0.1
geo=\$(xdotool getwindowgeometry --shell \"\$WID_DEC\" 2>/dev/null || true)
eval \"\$geo\" || true
: \${WIDTH:=1200}
: \${HEIGHT:=900}
input_x=\$(( WIDTH * 50 / 100 ))
input_y=\$(( HEIGHT * 88 / 100 ))
xdotool mousemove --window \"\$WID_DEC\" \"\$input_x\" \"\$input_y\" click 1 2>/dev/null || true
sleep 0.05
xdotool key --window \"\$WID_DEC\" ctrl+a 2>/dev/null || true
xdotool key --window \"\$WID_DEC\" Delete 2>/dev/null || true
xdotool type --delay 0 -- ${MSG_Q}
xdotool key --window \"\$WID_DEC\" Return
'" >/dev/null 2>&1 || true
sleep 0.8

ok=0
copy_mode="${LUCY_COPY_MODE_DUMMY:-auto}"
for _ in 1 2 3; do
  CHATGPT_INPUT_FOCUS_Y_OFFSET="${CHATGPT_INPUT_FOCUS_Y_OFFSET_DUMMY:-150}" \
  LUCY_COPY_MODE="$copy_mode" CHATGPT_WID_HEX="$dummy_wid" "$COPY" \
    >/tmp/verify_ui_dummy_pipe.out 2>/tmp/verify_ui_dummy_pipe.err || true
  if grep -q "^LUCY_ANSWER_${TOKEN}: " /tmp/verify_ui_dummy_pipe.out; then
    ok=1
    break
  fi
  sleep 0.6
done

if [[ "$ok" -ne 1 ]]; then
  echo "ERROR: dummy pipe did not return answer line" >&2
  cat /tmp/verify_ui_dummy_pipe.err >&2 || true
  exit 1
fi

echo "VERIFY_UI_DUMMY_PIPE_OK"
