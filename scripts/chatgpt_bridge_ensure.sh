#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
FILE_CALL="$ROOT/scripts/x11_file_call.sh"

PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"
URL="${CHATGPT_BRIDGE_URL:-https://chatgpt.com}"

# Si ya existe una ventana bridge (detectada por perfil), listo.
if wid="$("$GET_WID" 2>/dev/null)"; then
  echo "bridge_ensure: OK (existing wid=$wid)" 1>&2
  exit 0
fi

# Si no existe, la lanzamos en HOST con perfil separado.
"$FILE_CALL" "bash -lc 'mkdir -p "$PROFILE_DIR"; nohup google-chrome --user-data-dir="$PROFILE_DIR" --no-first-run --no-default-browser-check --new-window "$URL" >/tmp/lucy_bridge_chrome.log 2>&1 & echo LAUNCHED'" >/dev/null

# Esperar a que aparezca el WID bridge.
for _ in $(seq 1 60); do
  if wid="$("$GET_WID" 2>/dev/null)"; then
    echo "bridge_ensure: OK (launched wid=$wid)" 1>&2
    exit 0
  fi
  sleep 0.25
done

echo "bridge_ensure: ERROR no apareció el bridge (perfil=$PROFILE_DIR)" 1>&2
exit 1
