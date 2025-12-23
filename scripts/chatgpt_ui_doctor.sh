#!/usr/bin/env bash
set -euo pipefail

echo "== UI DOCTOR ==" >&2
echo "DATE: $(date -Is)" >&2

# Ensure X11 env (same policy as ask)
export DISPLAY="${DISPLAY:-:0}"
if [ -z "${XAUTHORITY:-}" ]; then
  if [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
  elif [ -f "/run/user/$UID/gdm/Xauthority" ]; then
    export XAUTHORITY="/run/user/$UID/gdm/Xauthority"
  else
    cand="$(ls -1 /run/user/$UID/.mutter-Xwaylandauth.* 2>/dev/null | head -n 1 || true)"
    [ -n "${cand:-}" ] && export XAUTHORITY="$cand"
  fi
fi

echo "DISPLAY=$DISPLAY" >&2
echo "XAUTHORITY=${XAUTHORITY:-<unset>}" >&2
[ -n "${XAUTHORITY:-}" ] && ls -l "$XAUTHORITY" >&2 || true

echo "--- deps ---" >&2
./scripts/check_ui_deps.sh >&2

echo "--- X11 geometry ---" >&2
xdotool getdisplaygeometry >&2

echo "--- active window ---" >&2
ACTIVE_DEC="$(xdotool getactivewindow 2>/dev/null || true)"
if [ -n "${ACTIVE_DEC:-}" ]; then
  printf "ACTIVE_DEC=%s\n" "$ACTIVE_DEC" >&2
  printf "ACTIVE_HEX=0x%08x\n" "$ACTIVE_DEC" >&2
  echo "ACTIVE_NAME=$(xdotool getwindowname "$ACTIVE_DEC" 2>/dev/null || echo '?')" >&2
else
  echo "ACTIVE_DEC=<none>" >&2
fi

echo "--- detect ChatGPT WID ---" >&2
WID="$(./scripts/chatgpt_get_wid.sh)"
echo "DETECTED_WID=$WID" >&2

WID_DEC=$((WID))
echo "WID_NAME=$(xdotool getwindowname "$WID_DEC" 2>/dev/null || echo '?')" >&2

echo "--- smoke ask ---" >&2
CHATGPT_WID_HEX="$WID" ./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK" >&2

echo "DOCTOR_OK" >&2
