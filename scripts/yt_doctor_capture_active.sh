#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

OUTDIR="${1:-/tmp/lucy_yt_doctor_$(date +%Y%m%d_%H%M%S)_$$}"
mkdir -p "$OUTDIR"

WID_DEC="$(xdotool getactivewindow 2>/dev/null || true)"
if [ -z "$WID_DEC" ]; then
  echo "ERROR_NO_ACTIVE_WINDOW" >&2
  exit 2
fi
WID_HEX="$(printf '0x%08x' "$WID_DEC")"
TITLE="$(xdotool getwindowname "$WID_DEC" 2>/dev/null || true)"

xdotool key --window "$WID_DEC" --clearmodifiers ctrl+l 2>/dev/null || true
sleep 0.08
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true
sleep 0.12

url=""
for _ in $(seq 1 12); do
  url="$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true)"
  if [ -z "$url" ]; then
    url="$(timeout 2s xsel --clipboard --output 2>/dev/null || true)"
  fi
  if [ -n "$url" ]; then
    break
  fi
  sleep 0.05
done
url="$(printf '%s' "$url" | tr -d '\r')"

pid="$(xprop -id "$WID_HEX" _NET_WM_PID 2>/dev/null | awk '{print $3}' | head -n 1)"
cmdline=""
if [ -n "$pid" ] && [ -r "/proc/$pid/cmdline" ]; then
  cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
fi

printf '%s' "$WID_DEC" > "$OUTDIR/wid_dec.txt"
printf '%s' "$WID_HEX" > "$OUTDIR/wid_hex.txt"
printf '%s' "$TITLE" > "$OUTDIR/title.txt"
printf '%s' "$url" > "$OUTDIR/url.txt"
printf '%s' "$pid" > "$OUTDIR/pid.txt"
printf '%s' "$cmdline" > "$OUTDIR/cmdline.txt"

if command -v import >/dev/null 2>&1; then
  import -window "$WID_HEX" "$OUTDIR/screenshot.png" 2>/dev/null || true
else
  echo "ERROR_NO_IMPORT: ImageMagick 'import' not found." >&2
fi

ts="$(date -Is)"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$ts" "$WID_DEC" "$WID_HEX" "$pid" "$url" "$TITLE" "$cmdline" >> "$OUTDIR/trace.tsv"

echo "OUTDIR=$OUTDIR"
echo "WID_DEC=$WID_DEC"
echo "WID_HEX=$WID_HEX"
