#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"
CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
PAID_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_chatgpt.sh"

PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}}"
URL="${CHATGPT_BRIDGE_URL:-https://chatgpt.com}"
CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"

# En modo paid/dummy, no abrimos ventanas nuevas.
if [[ "${CHATGPT_TARGET}" != "free" ]]; then
  if wid="$("$GET_WID" 2>/dev/null)"; then
    echo "bridge_ensure: OK (existing wid=$wid)" 1>&2
    exit 0
  fi
  if [[ "${CHATGPT_TARGET}" == "paid" ]] && [[ -x "$PAID_ENSURE" ]]; then
    if "$PAID_ENSURE" >/dev/null 2>&1; then
      if wid="$("$GET_WID" 2>/dev/null)"; then
        echo "bridge_ensure: OK (paid ensure wid=$wid)" 1>&2
        exit 0
      fi
    fi
  fi
  echo "bridge_ensure: ERROR no window for target=${CHATGPT_TARGET}" 1>&2
  exit 1
fi

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
