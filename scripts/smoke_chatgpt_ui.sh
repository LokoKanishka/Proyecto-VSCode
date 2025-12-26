#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$REPO_ROOT"

echo "== ROOT HEAD =="
git rev-parse --short HEAD
echo

echo "== WID (auto) =="
WID="$(./scripts/chatgpt_get_wid.sh 2>/dev/null || true)"
if [ -z "$WID" ]; then
  WID="$(./scripts/chatgpt_bridge_ensure.sh | tail -n 1)"
fi
echo "$WID"
echo

echo "== TEST 1: desde ROOT =="
OUT1="$(./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK" | tail -n 1 || true)"
echo "$OUT1"
echo

echo "== TEST 2: invocado desde SUBMODULE (cwd adentro) =="
OUT2="$(
  cd external/nodo-de-voz-modular-de-lucy
  "$REPO_ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" | tail -n 1 || true
)"
echo "$OUT2"
echo

echo "== ASSERT =="
echo "$OUT1" | grep -qE ': OK$'
echo "$OUT2" | grep -qE ': OK$'
echo "OK: smoke_chatgpt_ui"
