#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

# Si ya existe la ventana puente, devolvé el WID y listo.
if wid="$("$GET_WID" 2>/dev/null)"; then
  echo "$wid"
  exit 0
fi

# Si no existe, la abrimos en tu perfil Default (log-in normal).
CHROME_BIN="$(
  command -v google-chrome ||
  command -v google-chrome-stable ||
  command -v chromium-browser ||
  command -v chromium ||
  true
)"
[[ -n "${CHROME_BIN:-}" ]] || { echo "ERROR: no encontré Chrome/Chromium en PATH" >&2; exit 1; }

"$CHROME_BIN" \
  --profile-directory=Default \
  --app="https://chatgpt.com/" \
  --no-first-run \
  --no-default-browser-check \
  >/dev/null 2>&1 & disown || true

# Esperamos a que aparezca la ventana puente
for i in $(seq 1 30); do
  sleep 0.5
  if wid="$("$GET_WID" 2>/dev/null)"; then
    echo "$wid"
    exit 0
  fi
done

echo "ERROR: abrí Chrome pero no apareció la ventana puente (WM_CLASS chatgpt.com.*)" >&2
exit 2
