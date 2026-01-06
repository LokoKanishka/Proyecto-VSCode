#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/scripts/_verify_common.sh"

rm -f /tmp/a3_7_out.txt /tmp/a3_7_err.txt || true
python3 -u ./scripts/x11_dispatcher.py screenshot root > /tmp/a3_7_out.txt 2> /tmp/a3_7_err.txt || true

if ! grep -q '^PATH ' /tmp/a3_7_out.txt; then
  echo "VERIFY_A3_7_FAIL: no PATH"
  echo "--- STDOUT ---"; sed -n '1,120p' /tmp/a3_7_out.txt || true
  echo "--- STDERR ---"; sed -n '1,200p' /tmp/a3_7_err.txt || true
  exit 3
fi

P="$(sed -n 's/^PATH[[:space:]]\+\([^[:space:]]\+\).*/\1/p' /tmp/a3_7_out.txt | head -n 1)"
need_file "$P"
echo "VERIFY_A3_7_OK: $P"
