#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

CHATGPT_WID_HEX="${CHATGPT_WID_HEX:-}"
if [ -z "${CHATGPT_WID_HEX}" ]; then
  CHATGPT_WID_HEX="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /- Google Chrome$/ {print $1; exit}')"
fi
[ -n "${CHATGPT_WID_HEX}" ] || { echo "ERROR: no encontré Chrome"; exit 1; }

CHATGPT_WID_DEC=$((CHATGPT_WID_HEX))

xdotool windowactivate --sync "$CHATGPT_WID_DEC" >/dev/null 2>&1 || wmctrl -ia "$CHATGPT_WID_HEX" || true
sleep 0.20

# Geometría
eval "$(xdotool getwindowgeometry --shell "$CHATGPT_WID_DEC")"

# Scroll al final
xdotool key --window "$CHATGPT_WID_DEC" End || true
for _ in 1 2 3 4 5; do
  xdotool key --window "$CHATGPT_WID_DEC" Page_Down || true
  sleep 0.05
done

# Click centro-derecha (evita sidebar)
CX=$(( (WIDTH*3)/4 ))
CY=$(( HEIGHT/2 ))

xdotool mousemove --window "$CHATGPT_WID_DEC" "$CX" "$CY" click 1
sleep 0.06

xdotool key --window "$CHATGPT_WID_DEC" ctrl+a
sleep 0.05
xdotool key --window "$CHATGPT_WID_DEC" ctrl+c
sleep 0.12

xclip -o -selection clipboard 2>/dev/null || true
