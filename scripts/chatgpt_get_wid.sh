#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Consistencia X11 (DISPLAY, etc.) si el repo lo provee
if [[ -f "$SCRIPT_DIR/x11_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/x11_env.sh"
fi

# Overrides explícitos (útiles para tests)
if [[ -n "${LUCY_CHATGPT_WID_HEX:-}" ]]; then
  echo "$LUCY_CHATGPT_WID_HEX"; exit 0
fi
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  echo "$CHATGPT_WID_HEX"; exit 0
fi

# Preferencia #1 (la que queremos SIEMPRE):
# ventana puente en modo app => WM_CLASS "chatgpt.com.Google-chrome"
wid="$(
  wmctrl -lx 2>/dev/null | awk '
    {
      cls=tolower($3);
      if (cls ~ /^chatgpt\.com\./) { print $1; exit }
    }'
)"
if [[ -n "${wid:-}" ]]; then
  echo "$wid"; exit 0
fi

# Preferencia #2: si NO hay puente, mejor fallar antes que pegar en V.S.Code
# (igual dejamos un intento “seguro”: título con chatgpt pero NO V.S.Code)
wid="$(
  wmctrl -l 2>/dev/null | awk '
    {
      line=tolower($0);
      if (line ~ /chatgpt/ && line !~ /v\.s\.code/) { print $1; exit }
    }'
)"
if [[ -n "${wid:-}" ]]; then
  echo "$wid"; exit 0
fi

echo "ERROR: no encontré ventana ChatGPT puente (WM_CLASS chatgpt.com.*)." >&2
echo "Ventanas ChatGPT vistas (wmctrl -l):" >&2
wmctrl -l 2>/dev/null | grep -i chatgpt >&2 || true
exit 1
