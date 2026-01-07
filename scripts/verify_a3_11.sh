#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/scripts/_verify_common.sh"

WID="$(./scripts/chatgpt_get_wid.sh 2>/tmp/verify_a3_11_get_wid_err.txt || true)"
if [[ -z "${WID:-}" ]]; then
  echo "VERIFY_A3_11_FAIL: WID vacío"
  sed -n '1,120p' /tmp/verify_a3_11_get_wid_err.txt || true
  exit 2
fi

# Enter “en vacío” (menos intrusivo) — si el input está vacío, normalmente no manda nada.
python3 -u ./scripts/x11_dispatcher.py focus_window "$WID" >/tmp/a3_11_focus_out.txt 2>/tmp/a3_11_focus_err.txt || true
./scripts/chatgpt_clear_input_x11.sh
python3 -u ./scripts/x11_dispatcher.py send_keys "$WID" "Return" >/tmp/a3_11_keys_out.txt 2>/tmp/a3_11_keys_err.txt || true
./scripts/chatgpt_clear_input_x11.sh

if ! grep -q '^OK' /tmp/a3_11_focus_out.txt; then
  echo "VERIFY_A3_11_FAIL: focus_window"
  cat /tmp/a3_11_focus_out.txt || true
  cat /tmp/a3_11_focus_err.txt || true
  exit 3
fi
if ! grep -q '^OK' /tmp/a3_11_keys_out.txt; then
  echo "VERIFY_A3_11_FAIL: send_keys Return"
  cat /tmp/a3_11_keys_out.txt || true
  cat /tmp/a3_11_keys_err.txt || true
  exit 4
fi

echo "VERIFY_A3_11_OK: WID=$WID"
