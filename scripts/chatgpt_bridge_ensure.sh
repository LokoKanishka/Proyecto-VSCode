#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"

PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}}"
URL="${CHATGPT_BRIDGE_URL:-https://chatgpt.com}"
CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"

# Si ya existe una ventana bridge (detectada por perfil), listo.
if wid="$("$GET_WID" 2>/dev/null)"; then
  echo "bridge_ensure: OK (existing wid=$wid)" 1>&2
  exit 0
fi

# Si no existe, la lanzamos en HOST con perfil separado.
if [[ ! -x "$CHROME_OPEN" ]]; then
  echo "bridge_ensure: ERROR missing chatgpt_chrome_open.sh" 1>&2
  exit 1
fi

CHATGPT_OPEN_URL="$URL" \
  CHATGPT_CHROME_USER_DATA_DIR="$PROFILE_DIR" \
  CHATGPT_BRIDGE_CLASS="$CHATGPT_BRIDGE_CLASS" \
  "$CHROME_OPEN" >/dev/null 2>&1 || true

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
