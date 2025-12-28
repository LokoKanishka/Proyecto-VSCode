#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Lucy_Workspace/Proyecto-VSCode"
cd "$ROOT" || exit 1

export X11_FILE_IPC_DIR="$ROOT/diagnostics/x11_file_ipc"
source "$ROOT/scripts/x11_env.sh" || true
export CHATGPT_BRIDGE_PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"

OUTF="/tmp/ask_safe.out"
ERRF="/tmp/ask_safe.err"
: >"$OUTF"
: >"$ERRF"

# asegurar bridge + WID (rápido)
timeout 5s "$ROOT/scripts/chatgpt_bridge_ensure.sh" >>"$ERRF" 2>&1 || true
WID="$("$ROOT/scripts/chatgpt_get_wid.sh" 2>>"$ERRF" || true)"
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >>"$ERRF"
  exit 2
fi
export CHATGPT_WID_HEX="$WID"
echo "CHATGPT_WID_HEX=$CHATGPT_WID_HEX" >>"$ERRF"

# intento "rápido": máximo 10s (si no llega, corta con RC=124)
set +e
timeout 10s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "$@" >"$OUTF" 2>>"$ERRF"
RC=$?
set -e
echo "RC=$RC" >>"$ERRF"
exit "$RC"
