#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_ACCESS="$ROOT/scripts/x11_require_access.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
DISP="$ROOT/lucy_agents/x11_dispatcher.py"
ENSURE_FOCUS="$ROOT/scripts/chatgpt_ensure_input_focus.sh"

if [[ -x "$REQ_ACCESS" ]]; then
  "$REQ_ACCESS" >/dev/null 2>&1
fi

WID="${CHATGPT_WID_HEX:-}"
if [[ -z "${WID:-}" ]]; then
  WID="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  exit 3
fi
export CHATGPT_WID_HEX="$WID"

python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true

if [[ -x "$ENSURE_FOCUS" ]]; then
  "$ENSURE_FOCUS" "$WID" >/dev/null 2>/dev/null || true
fi

python3 -u "$DISP" send_keys "$WID" "ctrl+a" >/dev/null 2>/dev/null || true
python3 -u "$DISP" send_keys "$WID" "BackSpace" >/dev/null 2>/dev/null || true

echo "CHATGPT_INPUT_CLEARED=1"
