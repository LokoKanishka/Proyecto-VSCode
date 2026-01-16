#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

WID_HEX="${1:-}"
if [ -z "$WID_HEX" ]; then
  echo "ERROR_NO_WID_HEX" >&2
  exit 3
fi

OUTDIR="${2:-/tmp/lucy_yt_capture_$(date +%Y%m%d_%H%M%S)_$$}"
mkdir -p "$OUTDIR"

WID_DEC=$((WID_HEX))

xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
sleep 0.1
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

TITLE="$(xdotool getwindowname "$WID_DEC" 2>/dev/null || true)"
SCREENSHOT="$OUTDIR/screenshot.png"

if command -v import >/dev/null 2>&1; then
  import -window "$WID_HEX" "$SCREENSHOT" 2>/dev/null || true
else
  echo "ERROR_NO_IMPORT: ImageMagick 'import' not found." >&2
fi

printf '%s' "$TITLE" > "$OUTDIR/title.txt"
printf '%s' "$url" > "$OUTDIR/url.txt"

ts="$(date -Is)"
printf '%s\t%s\t%s\t%s\n' "$ts" "$WID_HEX" "$TITLE" "$url" >> "$OUTDIR/trace.tsv"

echo "OUTDIR=$OUTDIR"
echo "WID_HEX=$WID_HEX"
echo "TITLE=$TITLE"
echo "URL=$url"
echo "SCREENSHOT=$SCREENSHOT"
