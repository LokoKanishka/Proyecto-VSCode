#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi
if [ -x "$DIR/x11_require_access.sh" ]; then
  "$DIR/x11_require_access.sh"
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG="/tmp/lucy_chatgpt_ui_smoketest_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee "$LOG") 2>&1

echo "== DATE =="; date; echo
echo "== HEAD =="; git rev-parse HEAD; echo

echo "== WINDOWS (chatgpt) BEFORE =="
wmctrl -lx | grep -i chatgpt || true
echo

echo "== ENSURE BRIDGE =="
WID="$(./scripts/chatgpt_bridge_ensure.sh)"
echo "BRIDGE_WID=$WID"
wmctrl -lx | awk -v w="$WID" '$1==w {print "BRIDGE_LINE=", $0}'
echo

echo "== ASK #1 =="
CHATGPT_TIMEOUT_SEC="${CHATGPT_TIMEOUT_SEC:-60}" ./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK"
echo

echo "== ASK #2 =="
CHATGPT_TIMEOUT_SEC="${CHATGPT_TIMEOUT_SEC:-60}" ./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK"
echo

echo "== WINDOWS (chatgpt) AFTER =="
wmctrl -lx | grep -i chatgpt || true
echo

echo "== DONE =="
echo "LOG=$LOG"
