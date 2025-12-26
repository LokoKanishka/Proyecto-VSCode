#!/usr/bin/env bash
set -euo pipefail

# Overrides explícitos (tests / emergencias)
if [[ -n "${LUCY_CHATGPT_WID_HEX:-}" ]]; then
  echo "$LUCY_CHATGPT_WID_HEX"
  exit 0
fi
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  echo "$CHATGPT_WID_HEX"
  exit 0
fi

# Fuente preferida: ventana puente dedicada por WM_CLASS (lucy-chatgpt-bridge.*)
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
wid="$(
  wmctrl -lx 2>/dev/null | awk -v bc="$BRIDGE_CLASS" '
    BEGIN {
      bc=tolower(bc);
      gsub(/[][(){}.^$|*+?\\-]/,"\\\\&",bc); # escape regex
    }
    {
      cls=tolower($3);
      if (cls ~ ("^" bc "\\\\.")) { print $1; exit }
    }'
)"
if [[ -n "${wid:-}" ]]; then
  echo "$wid"
  exit 0
fi

# Fallback: ventana puente por sitio (WM_CLASS chatgpt.com.*)
wid="$(
  wmctrl -lx 2>/dev/null | awk '
    {
      cls=tolower($3);
      if (cls ~ /^chatgpt\.com\./) { print $1; exit }
    }'
)"

if [[ -n "${wid:-}" ]]; then
  echo "$wid"
  exit 0
fi

echo "ERROR: no encontré la ventana PUENTE (WM_CLASS chatgpt.com.*). Abrí la ventana ChatGPT puente y reintentá." >&2
exit 2
