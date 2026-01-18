#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

WID_HEX="${1:-}"
URL_PREFIX="${2:-}"
MAX_SECONDS="${3:-8}"

if [ -z "${WID_HEX:-}" ] || [ -z "${URL_PREFIX:-}" ]; then
  echo "USAGE: chrome_ensure_url_in_window.sh <WID_HEX> <url_prefix> [max_seconds]" >&2
  exit 2
fi
if ! printf '%s' "$URL_PREFIX" | grep -Eq '^(https?://|file://)'; then
  echo "ERROR_BAD_URL_PREFIX: <$URL_PREFIX>" >&2
  exit 2
fi

OUTROOT="/tmp/lucy_chrome_tab_lock"
mkdir -p "$OUTROOT"

WID_DEC=$((WID_HEX))
if [ "$WID_DEC" -le 0 ]; then
  echo "ERROR_INVALID_WID: $WID_HEX" >&2
  exit 3
fi

start_ts="$(date +%s)"
last_outdir=""

while true; do
  now_ts="$(date +%s)"
  if [ "$((now_ts - start_ts))" -ge "$MAX_SECONDS" ]; then
    break
  fi

  wmctrl -ia "$WID_HEX" 2>/dev/null || true
  xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
  sleep 0.12

  xdotool key --window "$WID_DEC" --clearmodifiers ctrl+l 2>/dev/null || true
  sleep 0.06
  xdotool type --window "$WID_DEC" --clearmodifiers --delay 2 "$URL_PREFIX" 2>/dev/null || true
  xdotool key --window "$WID_DEC" --clearmodifiers Return 2>/dev/null || true
  sleep 0.25

  iter_dir="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$"
  mkdir -p "$iter_dir"
  last_outdir="$iter_dir"

  set +e
  cap="$("$DIR/chrome_capture_active_tab.sh" "$WID_HEX" "$iter_dir" 2>/dev/null)"
  cap_rc=$?
  set -e
  if [ "$cap_rc" -eq 0 ]; then
    url="$(printf '%s\n' "$cap" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
    if [[ "$url" == "$URL_PREFIX"* ]]; then
      # Defocus omnibox selection (cosmetic/stability)
      xdotool key --window "$WID_DEC" --clearmodifiers Escape 2>/dev/null || true
      sleep 0.04
      echo "OUTDIR=$iter_dir"
      echo "WID_HEX=$WID_HEX"
      echo "URL=$url"
      exit 0
    fi
  fi

  sleep 0.25
done

echo "ERROR_URL_MISMATCH prefix=$URL_PREFIX" >&2
if [ -n "${last_outdir:-}" ]; then
  echo "OUTDIR=$last_outdir"
fi
exit 3
