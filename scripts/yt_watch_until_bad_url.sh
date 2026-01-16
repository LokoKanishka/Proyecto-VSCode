#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

# shellcheck source=/dev/null
. "$DIR/yt_doctor_rules.sh"

MAX_SECONDS="${1:-30}"
INTERVAL="${2:-1}"
WID_HEX="${3:-}"
OUTROOT="/tmp/lucy_yt_watch"
mkdir -p "$OUTROOT"

if [ -z "$WID_HEX" ]; then
  mapfile -t found < <(xdotool search --name "YouTube - Google Chrome" 2>/dev/null || true)
  if [ "${#found[@]}" -eq 0 ]; then
    echo "ERROR_NO_WID: no window matching 'YouTube - Google Chrome'" >&2
    exit 3
  fi
  if [ "${#found[@]}" -gt 1 ]; then
    echo "ERROR_MULTI_WID: multiple windows match 'YouTube - Google Chrome'" >&2
    for wid in "${found[@]}"; do
      name="$(xdotool getwindowname "$wid" 2>/dev/null || true)"
      printf 'WID_DEC=%s TITLE=%s\n' "$wid" "$name" >&2
    done
    exit 3
  fi
  WID_HEX="$(printf '0x%08x' "${found[0]}")"
fi

start_ts="$(date +%s)"
HIT_BAD_URL=""
SAVED="0"
OUTDIR=""
empty_count=0
EMPTY_LIMIT=3

while true; do
  now_ts="$(date +%s)"
  if [ "$((now_ts - start_ts))" -ge "$MAX_SECONDS" ]; then
    break
  fi

  iter_dir="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$"
  capture_out="$("$DIR/chrome_capture_active_tab.sh" "$WID_HEX" "$iter_dir" 2>/dev/null || true)"

  url_raw=""
  title_raw=""
  if [ -r "$iter_dir/url.txt" ]; then
    url_raw="$(cat "$iter_dir/url.txt")"
  fi
  if [ -r "$iter_dir/title.txt" ]; then
    title_raw="$(cat "$iter_dir/title.txt")"
  fi

  url_trim="$(printf '%s' "$url_raw" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

  if [ -z "$url_trim" ]; then
    empty_count=$((empty_count + 1))
    if [ "$empty_count" -ge "$EMPTY_LIMIT" ]; then
      OUTDIR="$iter_dir"
      echo "HIT_BAD_URL="
      echo "SAVED=0"
      echo "OUTDIR=$OUTDIR"
      exit 11
    fi
  else
    empty_count=0
  fi

  reason="$(_yt_bad_url_reason "$url_trim" "$title_raw")"
  if [ -n "$reason" ]; then
    HIT_BAD_URL="$reason"
    SAVED="1"
    OUTDIR="$iter_dir"
    if [ -r "$iter_dir/screenshot.png" ]; then
      cp "$iter_dir/screenshot.png" "$iter_dir/hit.png" 2>/dev/null || true
    fi
    break
  fi

  rm -rf "$iter_dir" 2>/dev/null || true
  sleep "$INTERVAL"
done

echo "HIT_BAD_URL=$HIT_BAD_URL"
echo "SAVED=$SAVED"
echo "OUTDIR=$OUTDIR"

if [ -n "$HIT_BAD_URL" ]; then
  exit 10
fi
exit 0
