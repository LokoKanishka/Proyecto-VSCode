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

_clear_clipboard() {
  if command -v xclip >/dev/null 2>&1; then
    printf '' | xclip -selection clipboard 2>/dev/null || true
  elif command -v xsel >/dev/null 2>&1; then
    printf '' | xsel --clipboard --input 2>/dev/null || true
  fi
}

_read_clipboard() {
  local text=""
  text="$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true)"
  if [ -z "$text" ]; then
    text="$(timeout 2s xsel --clipboard --output 2>/dev/null || true)"
  fi
  printf '%s' "$text"
}

_focus_omnibox() {
  local method="$1"
  case "$method" in
    ctrl+l)
      xdotool key --window "$WID_DEC" --clearmodifiers ctrl+l 2>/dev/null || true
      ;;
    alt+d)
      xdotool key --window "$WID_DEC" --clearmodifiers alt+d 2>/dev/null || true
      ;;
    F6)
      xdotool key --window "$WID_DEC" --clearmodifiers F6 2>/dev/null || true
      ;;
  esac
  sleep 0.08
}

wmctrl -ia "$WID_HEX" 2>/dev/null || true
xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
xdotool windowfocus --sync "$WID_DEC" 2>/dev/null || true
sleep 0.25

url=""
attempt=0
while [ "$attempt" -lt 5 ]; do
  attempt=$((attempt + 1))
  _clear_clipboard
  case "$attempt" in
    1|4) _focus_omnibox "ctrl+l" ;;
    2|5) _focus_omnibox "alt+d" ;;
    *) _focus_omnibox "F6" ;;
  esac
  xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true
  url=""
  for _ in $(seq 1 10); do
    sleep 0.1
    url="$(_read_clipboard)"
    url="$(printf '%s' "$url" | tr -d '\r')"
    if [ -n "$url" ]; then
      break
    fi
  done
  if printf '%s' "$url" | grep -Eq '^https?://'; then
    break
  fi
  sleep 0.1
done

TITLE="$(xdotool getwindowname "$WID_DEC" 2>/dev/null || true)"
SCREENSHOT="$OUTDIR/screenshot.png"

if command -v import >/dev/null 2>&1; then
  import -window "$WID_HEX" "$SCREENSHOT" 2>/dev/null || true
else
  echo "ERROR_NO_IMPORT: ImageMagick 'import' not found." >&2
  : > "$SCREENSHOT"
fi

printf '%s' "$TITLE" > "$OUTDIR/title.txt"
printf '%s' "$url" > "$OUTDIR/url.txt"
printf '%s' "$WID_HEX" > "$OUTDIR/wid_hex.txt"

ts="$(date -Is)"
printf '%s\t%s\t%s\t%s\n' "$ts" "$WID_HEX" "$TITLE" "$url" >> "$OUTDIR/trace.tsv"

echo "OUTDIR=$OUTDIR"
echo "WID_HEX=$WID_HEX"
echo "TITLE=$TITLE"
echo "URL=$url"
echo "SCREENSHOT=$SCREENSHOT"

if ! printf '%s' "$url" | grep -Eq '^https?://'; then
  echo "CAPTURE_URL_INVALID" >&2
  exit 11
fi
