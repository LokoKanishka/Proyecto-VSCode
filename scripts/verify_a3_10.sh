#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/scripts/_verify_common.sh"

WID="$(./scripts/chatgpt_get_wid.sh 2>/tmp/verify_a3_10_get_wid_err.txt || true)"
if [[ -z "${WID:-}" ]]; then
  echo "VERIFY_A3_10_FAIL: WID vacío"
  sed -n '1,120p' /tmp/verify_a3_10_get_wid_err.txt || true
  exit 2
fi

TXT="LUCY_A3_10_SMOKE_$(date +%H%M%S)"

python3 -u ./scripts/x11_dispatcher.py focus_window "$WID" >/tmp/a3_10_focus_out.txt 2>/tmp/a3_10_focus_err.txt || true
python3 -u ./scripts/x11_dispatcher.py type_text "$WID" "$TXT" >/tmp/a3_10_type_out.txt 2>/tmp/a3_10_type_err.txt || true

./scripts/chatgpt_clear_input_x11.sh

if ! grep -q '^OK' /tmp/a3_10_focus_out.txt; then
  echo "VERIFY_A3_10_FAIL: focus_window"
  cat /tmp/a3_10_focus_out.txt || true
  cat /tmp/a3_10_focus_err.txt || true
  exit 3
fi
if ! grep -q '^OK' /tmp/a3_10_type_out.txt; then
  echo "VERIFY_A3_10_FAIL: type_text"
  cat /tmp/a3_10_type_out.txt || true
  cat /tmp/a3_10_type_err.txt || true
  exit 4
fi

echo "VERIFY_A3_10_OK: WID=$WID"
