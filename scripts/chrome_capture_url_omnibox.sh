#!/usr/bin/env bash
set -euo pipefail

WID_HEX="${1:-}"
OUTDIR="${2:-}"

if [ -z "${WID_HEX:-}" ] || [ -z "${OUTDIR:-}" ]; then
  echo "USAGE: chrome_capture_url_omnibox.sh <WID_HEX> <outdir>" >&2
  exit 2
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR_MISSING_TOOL: $1" >&2; exit 3; }; }
need wmctrl
need xdotool
need xprop

# Clipboard read/set
CLIP_READ=""
CLIP_SET=""
if command -v xclip >/dev/null 2>&1; then
  CLIP_READ='xclip -o -selection clipboard'
  CLIP_SET='xclip -i -selection clipboard'
elif command -v xsel >/dev/null 2>&1; then
  CLIP_READ='xsel --clipboard --output'
  CLIP_SET='xsel --clipboard --input'
else
  echo "ERROR_NO_CLIP_TOOL: install xclip (recommended) or xsel" >&2
  exit 3
fi

mkdir -p "$OUTDIR"

# WID must be live
set +e
xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1
live_rc=$?
set -e
if [ "$live_rc" -ne 0 ]; then
  echo "ERROR_BADWINDOW: WID_HEX=$WID_HEX (xprop failed)" >&2
  exit 3
fi

WID_DEC=$((WID_HEX))

# Title (robusto)
title="$(xprop -id "$WID_HEX" _NET_WM_NAME 2>/dev/null | sed -n 's/.*= "\(.*\)".*/\1/p' | head -n 1 || true)"
printf '%s\n' "${title:-}" >"$OUTDIR/title.txt"

ok=0
url=""
active_before=""
active_after=""

for i in 1 2 3 4 5 6; do
  reset="LUCY_CLIP_RESET_$(date +%s)_$$_$i"

  # Reset clipboard to known token so we can detect stale reads
  printf '%s' "$reset" | eval "$CLIP_SET" >/dev/null 2>&1 || true
  sleep 0.03

  # Try to activate + focus
  wmctrl -ia "$WID_HEX" 2>/dev/null || true
  xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
  xdotool windowfocus --sync "$WID_DEC" 2>/dev/null || true
  sleep 0.08

  # Record active window (diagnostic)
  active_before="$(xdotool getactivewindow 2>/dev/null || true)"
  printf '%s\n' "$active_before" >"$OUTDIR/active_before_$i.txt"

  # Send keystrokes to the TARGET window (no depende del foco, pero igual activamos)
  xdotool key --window "$WID_DEC" --clearmodifiers Escape 2>/dev/null || true
  sleep 0.02
  xdotool key --window "$WID_DEC" --clearmodifiers ctrl+l 2>/dev/null || true
  sleep 0.02
  xdotool key --window "$WID_DEC" --clearmodifiers alt+d 2>/dev/null || true
  sleep 0.02
  xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true
  sleep 0.12

  active_after="$(xdotool getactivewindow 2>/dev/null || true)"
  printf '%s\n' "$active_after" >"$OUTDIR/active_after_$i.txt"

  got="$(eval "$CLIP_READ" 2>/dev/null | tr -d '\r' | head -n 1 || true)"
  printf '%s\n' "$got" >"$OUTDIR/clipboard_$i.txt"

  # If clipboard didn't change, retry
  if [ -z "${got:-}" ] || [ "$got" = "$reset" ]; then
    sleep 0.10
    continue
  fi

  # Accept URL-ish strings only
  if printf '%s' "$got" | grep -Eq '^(https?://|chrome://|edge://)'; then
    url="$got"
    ok=1
    break
  fi

  sleep 0.10
done

printf '%s\n' "$ok" >"$OUTDIR/ok.txt"
printf '%s\n' "${url:-}" >"$OUTDIR/url.txt"

echo "OK=$ok"
echo "WID_HEX=$WID_HEX"
echo "TITLE=${title:-}"
echo "URL=${url:-}"
echo "OUTDIR=$OUTDIR"
