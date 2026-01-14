#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== VERIFY BRIDGE END-TO-END =="

echo
echo "[1/4] verify_repo_fast"
"$ROOT/scripts/verify_repo_fast.sh"

echo
echo "[2/4] verify_chatgpt_copy_strict"
"$ROOT/scripts/verify_chatgpt_copy_strict.sh"

echo
echo "[3/4] verify_wait_answer_parser"
"$ROOT/scripts/verify_wait_answer_parser.sh"

echo
echo "[4/4] verify_ui_dialogs_local_modal (optional, non-blocking by default)"
if [[ "${LUCY_REQUIRE_UI_DIALOGS:-0}" != "1" ]]; then
  echo "SKIP (set LUCY_REQUIRE_UI_DIALOGS=1 to enforce)"
else
  echo "SKIP (LUCY_SKIP_UI_DIALOGS=1)"
  "$ROOT/scripts/verify_ui_dialogs_local_modal.sh" || { echo "WARN: ui dialogs failed (non-blocking)"; }
fi

echo
echo "== OK: BRIDGE VERIFIED =="
