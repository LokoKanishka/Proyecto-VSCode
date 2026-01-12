#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
DISP="$ROOT/lucy_agents/x11_dispatcher.py"

WID_HEX="${1:-${CHATGPT_WID_HEX:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  exit 3
fi

WID_DEC="$(printf "%d" "$WID_HEX" 2>/dev/null || echo 0)"
if [[ "${WID_DEC}" -le 0 ]]; then
  echo "ERROR: WID invalido: ${WID_HEX}" >&2
  exit 3
fi

X_PCT_DEFAULT="${CHATGPT_INPUT_FOCUS_X_PCT:-70}"
Y_OFFSET_DEFAULT="${CHATGPT_INPUT_FOCUS_Y_OFFSET:-220}"
Y_STEP="${CHATGPT_INPUT_FOCUS_Y_STEP:-40}"
MAX_TRIES="${CHATGPT_INPUT_FOCUS_MAX_TRIES:-5}"
X_ALT_LOW="${CHATGPT_INPUT_FOCUS_X_ALT_LOW:-65}"
X_ALT_HIGH="${CHATGPT_INPUT_FOCUS_X_ALT_HIGH:-75}"
JITTER_PX="${CHATGPT_INPUT_FOCUS_JITTER_PX:-0}"

STAMP="$(date +%s%N 2>/dev/null || date +%s)"
FOCUS_TOKEN_BASE="__LUCY_INPUT_PROBE_${STAMP}__"

LOG_DIR="${FOCUS_LOG_DIR:-${LUCY_ASK_TMPDIR:-}}"
ATTEMPTS_PATH="${FOCUS_ATTEMPTS_PATH:-}"
PROBE_COPY_PATH="${FOCUS_PROBE_COPY_PATH:-}"
FAIL_PATH="${FOCUS_FAIL_PATH:-}"
if [[ -n "${LOG_DIR:-}" ]]; then
  mkdir -p "$LOG_DIR" 2>/dev/null || true
  : "${ATTEMPTS_PATH:=$LOG_DIR/focus_attempts.txt}"
  : "${PROBE_COPY_PATH:=$LOG_DIR/probe_copy.txt}"
  : "${FAIL_PATH:=$LOG_DIR/focus_probe_fail.txt}"
else
  : "${ATTEMPTS_PATH:=/tmp/lucy_focus_attempts_${STAMP}.txt}"
  : "${PROBE_COPY_PATH:=/tmp/lucy_focus_probe_copy_${STAMP}.txt}"
  : "${FAIL_PATH:=/tmp/lucy_focus_probe_fail_${STAMP}.txt}"
fi

get_geometry() {
  local geo
  geo="$("$HOST_EXEC" "xdotool getwindowgeometry --shell ${WID_DEC}" 2>/dev/null || true)"
  eval "$geo" || true
  : "${WIDTH:=1200}"
  : "${HEIGHT:=900}"
  printf '%s %s\n' "$WIDTH" "$HEIGHT"
}

calc_click() {
  local width="$1" height="$2" attempt="$3"
  local x_pct="$X_PCT_DEFAULT"
  if [[ "$attempt" -eq 2 ]]; then
    x_pct="$X_ALT_LOW"
  elif [[ "$attempt" -ge 3 ]]; then
    if (( attempt % 2 == 1 )); then
      x_pct="$X_ALT_HIGH"
    else
      x_pct="$X_ALT_LOW"
    fi
  fi
  local y_offset=$(( Y_OFFSET_DEFAULT + (attempt - 1) * Y_STEP ))
  local x=$(( width * x_pct / 100 ))
  local y=$(( height - y_offset ))
  local min_y=$(( height - 150 ))
  if [[ "$y" -gt "$min_y" ]]; then
    y="$min_y"
  fi
  if [[ "$y" -lt 50 ]]; then
    y=$(( height / 2 ))
  fi
  if [[ "$JITTER_PX" -gt 0 ]]; then
    local jitter=$(( (RANDOM % (JITTER_PX * 2 + 1)) - JITTER_PX ))
    x=$(( x + jitter ))
    y=$(( y + jitter ))
  fi
  printf '%s %s %s\n' "$x" "$y" "$x_pct"
}

run_probe() {
  local token="$1"
  local x="$2"
  local y="$3"
  local out
  local script="WID_HEX='${WID_HEX}' WID_DEC='${WID_DEC}' TOKEN='${token}' PROBE_X='${x}' PROBE_Y='${y}'; set -euo pipefail; wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; sleep 0.12; xdotool key --window \"\$WID_DEC\" Escape 2>/dev/null || true; xdotool key --window \"\$WID_DEC\" Escape 2>/dev/null || true; xdotool mousemove --window \"\$WID_DEC\" \"\$PROBE_X\" \"\$PROBE_Y\" click 1 2>/dev/null || true; sleep 0.10; xdotool type --window \"\$WID_DEC\" --delay 1 --clearmodifiers \"\$TOKEN\" 2>/dev/null || true; sleep 0.08; xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+a 2>/dev/null || true; sleep 0.08; xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+c 2>/dev/null || true; sleep 0.15; t=''; for i in \$(seq 1 12); do t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true); [[ -n \"\$t\" ]] && break; t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true); [[ -n \"\$t\" ]] && break; sleep 0.05; done; printf '%s' \"\$t\"; xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+a 2>/dev/null || true; sleep 0.05; xdotool key --window \"\$WID_DEC\" --clearmodifiers BackSpace 2>/dev/null || true"
  
  local cmd="WID_HEX='${WID_HEX}' WID_DEC='${WID_DEC}' TOKEN='${token}' PROBE_X='${x}' PROBE_Y='${y}'; "
  cmd+="set -euo pipefail; "
  cmd+="wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; "
  cmd+="xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; "
  cmd+="sleep 0.12; "
  cmd+="xdotool key --window \"\$WID_DEC\" Escape 2>/dev/null || true; "
  cmd+="xdotool key --window \"\$WID_DEC\" Escape 2>/dev/null || true; "
  cmd+="xdotool mousemove --window \"\$WID_DEC\" \"\$PROBE_X\" \"\$PROBE_Y\" click 1 2>/dev/null || true; "
  cmd+="sleep 0.12; "
  cmd+="xdotool type --window \"\$WID_DEC\" --delay 1 --clearmodifiers \"\$TOKEN\" 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  cmd+="xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+a 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  cmd+="xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+c 2>/dev/null || true; "
  cmd+="sleep 0.20; "
  cmd+="t=''; "
  cmd+="for i in \$(seq 1 12); do "
  cmd+="  t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  sleep 0.08; "
  cmd+="done; "
  cmd+="printf '%s' \"\$t\"; "
  cmd+="xdotool key --window \"\$WID_DEC\" --clearmodifiers ctrl+a 2>/dev/null || true; "
  cmd+="sleep 0.05; "
  cmd+="xdotool key --window \"\$WID_DEC\" --clearmodifiers BackSpace 2>/dev/null || true"

  out="$("$HOST_EXEC" "$cmd")"
  printf '%s' "$out"
}

read -r WIDTH HEIGHT < <(get_geometry)
attempt=1
while [[ "$attempt" -le "$MAX_TRIES" ]]; do
  read -r cx cy x_pct < <(calc_click "$WIDTH" "$HEIGHT" "$attempt")
  token="${FOCUS_TOKEN_BASE}_${attempt}__"
  ts="$(date +%s)"
  printf 'ts=%s attempt=%s x=%s y=%s x_pct=%s token=%s\n' "$ts" "$attempt" "$cx" "$cy" "$x_pct" "$token" >>"$ATTEMPTS_PATH" 2>/dev/null || true
  clip="$(run_probe "$token" "$cx" "$cy")"
  printf '%s' "$clip" >"$PROBE_COPY_PATH" 2>/dev/null || true
  if [[ "${clip}" == *"${token}"* ]]; then
    if [[ "${FOCUS_RETURN_COPY:-0}" -eq 1 ]]; then
      clean="${clip//${token}/}"
      printf '%s' "$clean"
    fi
    echo "FOCUS_OK token=${token} attempt=${attempt} x=${cx} y=${cy}" >&2
    exit 0
  fi
  attempt=$((attempt + 1))
done

{
  echo "FOCUS_FAIL attempts=${MAX_TRIES} wid=${WID_HEX} width=${WIDTH} height=${HEIGHT}"
  tail -n 10 "$ATTEMPTS_PATH" 2>/dev/null || true
} >"$FAIL_PATH" 2>/dev/null || true

if [[ -x "$DISP" ]]; then
  python3 -u "$DISP" screenshot "$WID_HEX" >/dev/null 2>&1 || true
fi

echo "FOCUS_FAIL attempts=${MAX_TRIES} wid=${WID_HEX}" >&2
exit 1
