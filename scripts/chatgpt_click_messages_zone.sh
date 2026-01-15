#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

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

X_PCT="${CHATGPT_MESSAGES_CLICK_X_PCT:-40}"
Y_PCT="${CHATGPT_MESSAGES_CLICK_Y_PCT:-50}"
JITTER_PX="${CHATGPT_MESSAGES_CLICK_JITTER_PX:-0}"

geo="$("$HOST_EXEC" "xdotool getwindowgeometry --shell ${WID_DEC}" 2>/dev/null || true)"
eval "$geo" || true
: "${WIDTH:=1200}"
: "${HEIGHT:=900}"

px=$(( WIDTH * X_PCT / 100 ))
py=$(( HEIGHT * Y_PCT / 100 ))
if [[ "$JITTER_PX" -gt 0 ]]; then
  jitter=$(( (RANDOM % (JITTER_PX * 2 + 1)) - JITTER_PX ))
  px=$(( px + jitter ))
  py=$(( py + jitter ))
fi

cmd="PX='${px}' PY='${py}' WID_HEX='${WID_HEX}' WID_DEC='${WID_DEC}'; "
cmd+="set -euo pipefail; "
cmd+="wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; "
cmd+="xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; "
cmd+="sleep 0.15; "
cmd+="xdotool key --window "$WID_DEC" --clearmodifiers Escape 2>/dev/null || true; "
cmd+="xdotool mousemove --window \"\$WID_DEC\" \"\$PX\" \"\$PY\" click 1 2>/dev/null || true; "
cmd+="sleep 0.10; "
cmd+="xdotool key --window "$WID_DEC" --clearmodifiers ctrl+a 2>/dev/null || true; "
cmd+="sleep 0.10; "
cmd+="xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true; "
cmd+="sleep 0.20; "
cmd+="t=''; "
cmd+="for i in \$(seq 1 15); do "
cmd+="  t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true); "
cmd+="  [[ -n \"\$t\" ]] && break; "
cmd+="  t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true); "
cmd+="  [[ -n \"\$t\" ]] && break; "
cmd+="  sleep 0.08; "
cmd+="done; "
cmd+="printf '%s' \"\$t\""

echo "MESSAGES_ZONE_CLICK_OK x=${px} y=${py} x_pct=${X_PCT} y_pct=${Y_PCT} jitter=${JITTER_PX}" >&2
"$HOST_EXEC" "$cmd"
