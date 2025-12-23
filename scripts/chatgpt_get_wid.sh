#!/usr/bin/env bash
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"

# si XAUTHORITY no está y ~/.Xauthority no existe, probamos rutas típicas (sin romper si no están)
if [ -z "${XAUTHORITY:-}" ] && [ ! -f "$HOME/.Xauthority" ]; then
  for cand in "/run/user/$UID/gdm/Xauthority" "/run/user/$UID/.Xauthority"; do
    if [ -f "$cand" ]; then export XAUTHORITY="$cand"; break; fi
  done
fi

# 1) override explícito
if [ -n "${CHATGPT_WID_HEX:-}" ]; then
  echo "$CHATGPT_WID_HEX"
  exit 0
fi

# 2) si la ventana activa parece ser el tab que queremos, usarla
ACTIVE_DEC="$(xdotool getactivewindow 2>/dev/null || true)"
if [ -n "${ACTIVE_DEC:-}" ]; then
  NAME="$(xdotool getwindowname "$ACTIVE_DEC" 2>/dev/null || true)"
  if echo "$NAME" | grep -qi "google chrome" && echo "$NAME" | grep -qiE "LUCY_REQ_|ChatGPT"; then
    printf '0x%08x\n' "$ACTIVE_DEC"
    exit 0
  fi
fi

# 3) preferir tabs que creamos nosotros
WID="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /LUCY_REQ_/ && /- Google Chrome$/ {print $1; exit}')"
# 4) fallback “ChatGPT”
if [ -z "${WID:-}" ]; then
  WID="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /ChatGPT/ && /- Google Chrome$/ {print $1; exit}')"
fi
# 5) fallback “chatgpt” (minúsculas)
if [ -z "${WID:-}" ]; then
  WID="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /chatgpt/ && /- Google Chrome$/ {print $1; exit}')"
fi
# 6) último fallback: primer Chrome que NO sea el tab de VSCode
if [ -z "${WID:-}" ]; then
  WID="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /- Google Chrome$/ && $0 !~ /V\.S\.Code|Visual Studio Code/ {print $1; exit}')"
fi

if [ -z "${WID:-}" ]; then
  echo "ERROR: no encontré ninguna ventana de Chrome usable." >&2
  wmctrl -l | awk 'BEGIN{IGNORECASE=1} /- Google Chrome$/ {print "CAND:",$0}' >&2 || true
  exit 2
fi

echo "$WID"
