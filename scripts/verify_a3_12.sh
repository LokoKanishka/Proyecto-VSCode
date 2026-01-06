#!/usr/bin/env bash
set -euo pipefail

cd "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

unset X11_FILE_IPC_DIR || true
unset CHATGPT_WID_HEX || true

# Resolver WID (auto-abrir si hace falta)
WID="$(./scripts/chatgpt_get_wid.sh 2>/tmp/verify_a3_12_get_wid_err.txt || true)"
if [[ -z "${WID:-}" ]]; then
  echo "VERIFY_A3_12_FAIL: WID vacío"
  sed -n '1,120p' /tmp/verify_a3_12_get_wid_err.txt || true
  exit 2
fi

ANS="$(./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK" 2>/tmp/verify_a3_12_ask_err.txt || true)"
if [[ -z "${ANS:-}" ]]; then
  echo "VERIFY_A3_12_FAIL: ANS vacío"
  sed -n '1,220p' /tmp/verify_a3_12_ask_err.txt || true
  exit 3
fi

echo "VERIFY_A3_12_OK: $ANS"
