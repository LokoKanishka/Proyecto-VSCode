#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

# Permitir override explícito
CHATGPT_WID_HEX="${CHATGPT_WID_HEX:-}"
if [ -z "${CHATGPT_WID_HEX}" ] && [ -n "${LUCY_CHATGPT_WID_HEX:-}" ]; then
  CHATGPT_WID_HEX="$LUCY_CHATGPT_WID_HEX"
fi

# Si no vino seteado, usar el selector "seguro" (ventana puente WM_CLASS chatgpt.com.*)
if [ -z "${CHATGPT_WID_HEX}" ] && [ -x "$DIR/chatgpt_get_wid.sh" ]; then
  CHATGPT_WID_HEX="$("$DIR/chatgpt_get_wid.sh" 2>/dev/null || true)"
fi

[ -n "${CHATGPT_WID_HEX}" ] || {
  echo "ERROR: no encontré la ventana PUENTE (WM_CLASS chatgpt.com.*). Abrí la ventana ChatGPT puente o seteá CHATGPT_WID_HEX." >&2
  exit 1
}

CHATGPT_WID_DEC=$((CHATGPT_WID_HEX))
# Sanity check: asegurate de que es la ventana puente (chatgpt.com o lucy-chatgpt-bridge)
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
WMCLASS_LINE="$(xprop -id "$CHATGPT_WID_DEC" WM_CLASS 2>/dev/null || true)"
echo "$WMCLASS_LINE" | grep -qi 'chatgpt\.com' || echo "$WMCLASS_LINE" | grep -Fqi "$BRIDGE_CLASS" || {
  echo "ERROR: WID no parece ventana puente (WM_CLASS != chatgpt.com ni $BRIDGE_CLASS). WID=$CHATGPT_WID_HEX" >&2
  echo "WM_CLASS=$WMCLASS_LINE" >&2
  exit 2
}


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
