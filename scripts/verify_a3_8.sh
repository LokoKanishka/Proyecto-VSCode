#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/scripts/_verify_common.sh"

WID="$(./scripts/chatgpt_get_wid.sh 2>/tmp/verify_a3_8_get_wid_err.txt || true)"
if [[ -z "${WID:-}" ]]; then
  echo "VERIFY_A3_8_FAIL: WID vacío"
  sed -n '1,120p' /tmp/verify_a3_8_get_wid_err.txt || true
  exit 2
fi

rm -f /tmp/a3_8_out.txt /tmp/a3_8_err.txt || true
python3 -u ./lucy_agents/x11_dispatcher.py screenshot "$WID" > /tmp/a3_8_out.txt 2> /tmp/a3_8_err.txt || true

if ! grep -q '^PATH ' /tmp/a3_8_out.txt; then
  echo "VERIFY_A3_8_FAIL: no PATH (WID=$WID)"
  echo "--- STDOUT ---"; sed -n '1,120p' /tmp/a3_8_out.txt || true
  echo "--- STDERR ---"; sed -n '1,200p' /tmp/a3_8_err.txt || true
  exit 3
fi

P="$(sed -n 's/^PATH[[:space:]]\+\([^[:space:]]\+\).*/\1/p' /tmp/a3_8_out.txt | head -n 1)"
need_file "$P"
echo "VERIFY_A3_8_OK: WID=$WID PATH=$P"
