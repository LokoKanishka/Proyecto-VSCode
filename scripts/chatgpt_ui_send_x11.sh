#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIR="$SCRIPT_DIR"

if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

if [ -x "$DIR/x11_require_access.sh" ]; then
  "$DIR/x11_require_access.sh"
fi

# Auto-detect/ensure ChatGPT window id if not provided (VENTANA PUENTE)
if [ -z "${CHATGPT_WID_HEX:-}" ]; then
  if [ -x "$DIR/chatgpt_bridge_ensure.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_bridge_ensure.sh")"
  elif [ -x "$DIR/chatgpt_get_wid.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_get_wid.sh" || true)"
  fi
  export CHATGPT_WID_HEX
fi

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "USO: $0 \"mensaje a pegar y enviar\"" >&2
  exit 2
fi

[ -n "${CHATGPT_WID_HEX:-}" ] || { echo "ERROR: no hay CHATGPT_WID_HEX"; exit 2; }

CHATGPT_WID_HEX="$CHATGPT_WID_HEX" "${REPO_ROOT}/scripts/chatgpt_focus_paste.sh" "$MSG" >/dev/null
xdotool key --window "$((CHATGPT_WID_HEX))" Return
echo "SENT_OK"
