#!/usr/bin/env bash
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WID_HEX="${CHATGPT_WID_HEX:-$("$DIR/chatgpt_get_wid.sh")}"
WID_DEC=$((WID_HEX))

xdotool windowactivate --sync "$WID_DEC" >/dev/null 2>&1 || wmctrl -ia "$WID_HEX" || true
sleep 0.15

eval "$(xdotool getwindowgeometry --shell "$WID_DEC")"

CX=$(( (WIDTH*70)/100 ))
CY=$(( (HEIGHT*55)/100 ))

xdotool mousemove --window "$WID_DEC" "$CX" "$CY" click 1
sleep 0.08
xdotool key --window "$WID_DEC" End || true
sleep 0.05

xdotool key --window "$WID_DEC" ctrl+a
sleep 0.03
xdotool key --window "$WID_DEC" ctrl+c
sleep 0.12

xclip -o -selection clipboard 2>/dev/null || true
