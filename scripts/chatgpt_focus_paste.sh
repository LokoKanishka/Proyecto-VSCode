#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

TEXT="${1:-Respondé exactamente con: OK}"

CHATGPT_WID_HEX="${CHATGPT_WID_HEX:-}"
if [ -z "${CHATGPT_WID_HEX}" ]; then
  echo "ERROR: seteá CHATGPT_WID_HEX=0x.... (ej: 0x01e00017)" >&2
  exit 2
fi

CHATGPT_WID_DEC=$((CHATGPT_WID_HEX))

# Activar ventana
xdotool windowactivate --sync "$CHATGPT_WID_DEC" >/dev/null 2>&1 || wmctrl -ia "$CHATGPT_WID_HEX" || true
sleep 0.25

# Geometría
eval "$(xdotool getwindowgeometry --shell "$CHATGPT_WID_DEC")"

# Click abajo-derecha (evita sidebar)
CX=$(( (WIDTH*3)/4 ))
CY=$(( HEIGHT-150 ))

xdotool mousemove --window "$CHATGPT_WID_DEC" "$CX" "$CY" click 1
sleep 0.10

# Limpiar y pegar (Delete es más seguro que BackSpace)
xdotool key --window "$CHATGPT_WID_DEC" ctrl+a
sleep 0.03
xdotool key --window "$CHATGPT_WID_DEC" Delete
sleep 0.05

printf '%s' "$TEXT" | xclip -selection clipboard
xdotool key --window "$CHATGPT_WID_DEC" ctrl+v

echo "PASTED_OK"
