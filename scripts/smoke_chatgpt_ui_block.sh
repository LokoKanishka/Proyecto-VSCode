#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/.." && pwd)"

echo "== ROOT HEAD =="
( cd "$REPO_ROOT" && git rev-parse --short HEAD )
echo

echo "== WID (auto) =="
"$DIR/chatgpt_get_wid.sh" || true
echo

OUT="$("$DIR/chatgpt_ui_ask_block_x11.sh" "Escribí exactamente 3 líneas: A (primera), B (segunda), C (tercera).")"

echo "== OUT =="
printf '%s\n' "$OUT"
echo

# Assert estricto: 3 primeras líneas A/B/C
L1="$(printf '%s\n' "$OUT" | sed -n '1p')"
L2="$(printf '%s\n' "$OUT" | sed -n '2p')"
L3="$(printf '%s\n' "$OUT" | sed -n '3p')"

[ "$L1" = "A" ] || { echo "FAIL: L1=$L1"; exit 1; }
[ "$L2" = "B" ] || { echo "FAIL: L2=$L2"; exit 1; }
[ "$L3" = "C" ] || { echo "FAIL: L3=$L3"; exit 1; }

echo "OK: smoke_chatgpt_ui_block"
