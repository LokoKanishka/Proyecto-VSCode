#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

# Si ya existe la ventana puente dedicada (WM_CLASS ${CHATGPT_BRIDGE_CLASS}), devolvé el WID y listo.
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
wid="$(
  wmctrl -lx 2>/dev/null | awk -v bc="$BRIDGE_CLASS" '
    BEGIN {
      bc=tolower(bc);
      gsub(/[][(){}.^$|*+?\-]/,"\\&",bc); # escape regex
    }
    {
      cls=tolower($3);
      if (cls ~ ("^" bc "\\.")) { print $1; exit }
    }'
)"
if [[ -n "${wid:-}" ]]; then
  echo "$wid"
  exit 0
fi

# Si no existe, la abrimos como "ventana puente" dedicada.
CHROME_BIN="$(
  command -v google-chrome ||
  command -v google-chrome-stable ||
  command -v chromium-browser ||
  command -v chromium ||
  true
)"
[[ -n "${CHROME_BIN:-}" ]] || { echo "ERROR: no encontré Chrome/Chromium en PATH" >&2; exit 1; }

BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
BRIDGE_URL="${CHATGPT_BRIDGE_URL:-https://chatgpt.com/}"
BRIDGE_USER_DATA_DIR="${CHATGPT_BRIDGE_USER_DATA_DIR:-$HOME/.config/lucy-chatgpt-bridge-chrome}"
mkdir -p "$BRIDGE_USER_DATA_DIR"

"$CHROME_BIN" \
  --user-data-dir="$BRIDGE_USER_DATA_DIR" \
  --profile-directory=Default \
  --class="$BRIDGE_CLASS" \
  --app="$BRIDGE_URL" \
  --no-first-run \
  --no-default-browser-check \
  >/dev/null 2>&1 & disown || true

# Esperamos a que aparezca la ventana puente
for i in $(seq 1 30); do
  sleep 0.5
  wid="$(
    wmctrl -lx 2>/dev/null | awk -v bc="$BRIDGE_CLASS" '
      BEGIN {
        bc=tolower(bc);
        gsub(/[][(){}.^$|*+?\-]/,"\\&",bc);
      }
      {
        cls=tolower($3);
        if (cls ~ ("^" bc "\\.")) { print $1; exit }
      }'
  )"
  if [[ -n "${wid:-}" ]]; then
    echo "$wid"
    exit 0
  fi
done

echo "ERROR: abrí Chrome pero no apareció la ventana puente (WM_CLASS ${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}.*)" >&2
exit 2
