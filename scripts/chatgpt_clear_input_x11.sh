#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_ACCESS="$ROOT/scripts/x11_require_access.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
DISP="$ROOT/scripts/x11_dispatcher.py"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

if [[ -x "$REQ_ACCESS" ]]; then
  "$REQ_ACCESS" >/dev/null 2>&1
fi

WID="${CHATGPT_WID_HEX:-}"
if [[ -z "${WID:-}" ]]; then
  WID="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  exit 3
fi
export CHATGPT_WID_HEX="$WID"

python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true

# click en zona input (abajo-centro) usando host xdotool, como copy/ask
if [[ -x "$HOST_EXEC" ]]; then
  "$HOST_EXEC" "bash -lc '
set -euo pipefail
WID_HEX=\"$WID\"
WID_DEC=\$(printf \"%d\" \"\$WID_HEX\")
wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true
xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true
geo=\$(xdotool getwindowgeometry --shell \"\$WID_DEC\" 2>/dev/null || true)
eval \"\$geo\" || true
: \${WIDTH:=1200}
: \${HEIGHT:=900}
px=\$(( WIDTH * 55 / 100 ))
py=\$(( HEIGHT * 92 / 100 ))
xdotool mousemove --window \"\$WID_DEC\" \"\$px\" \"\$py\" click 1 2>/dev/null || true
xdotool key --window \"\$WID_DEC\" Escape 2>/dev/null || true
'" >/dev/null 2>/dev/null || true
fi

python3 -u "$DISP" send_keys "$WID" "ctrl+a" >/dev/null 2>/dev/null || true
python3 -u "$DISP" send_keys "$WID" "BackSpace" >/dev/null 2>/dev/null || true

echo "CHATGPT_INPUT_CLEARED=1"
