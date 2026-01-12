#!/usr/bin/env bash
# --- A3.12 fallback: resolver WID vía selector estable ---
# Si no está seteado CHATGPT_WID_HEX, lo resolvemos con scripts/chatgpt_get_wid.sh
# (que en nuestro entorno ya usa x11_host_exec.sh, así funciona desde sandbox).
if [[ -z "${CHATGPT_WID_HEX:-}" ]]; then
  ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
  GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
  if [[ -x "$GET_WID" ]]; then
    CHATGPT_WID_HEX="$("$GET_WID" 2>/dev/null || true)"
    export CHATGPT_WID_HEX
  fi
fi
# -------------------------------------------------------

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

# Phase 4 extension: robust send trigger
# Evitamos el dispatcher (que hace wmctrl -R) para no perder el foco interno del input.
# Ya aseguramos foco en chatgpt_focus_paste.sh -> chatgpt_ensure_input_focus.sh.
WID_HEX="${CHATGPT_WID_HEX}"
WID_DEC="$((WID_HEX))"

# Margen generoso para que el paste se procese por el DOM de la UI
sleep 0.8

# Enviamos Return directamente a la ventana activa
xdotool key --window "$WID_DEC" --clearmodifiers Return
sleep 0.2
# Enviamos un segundo Return opcional por si el primero fue ignorado por "loading state"
# xdotool key --window "$WID_DEC" --clearmodifiers Return

echo "SENT_OK"
