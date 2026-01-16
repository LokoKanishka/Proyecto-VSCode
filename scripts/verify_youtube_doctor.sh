#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

echo "[YT-DOCTOR] Launching clean Chrome..." >&2
"$DIR/youtube_open_clean.sh" "https://www.youtube.com/" >/dev/null 2>&1 || true
sleep 2

if command -v xdotool >/dev/null 2>&1; then
  wid="$(xdotool search --onlyvisible --class 'google-chrome' 2>/dev/null | tail -n 1 || true)"
  if [ -n "$wid" ]; then
    xdotool windowactivate --sync "$wid" 2>/dev/null || true
    sleep 0.2
  fi
fi

echo "[YT-DOCTOR] Watching for BAD_URL (25s)..." >&2
output="$($DIR/yt_watch_until_bad_url.sh 25 1 || true)"

echo "$output"

hit="$(printf '%s' "$output" | awk -F= '/^HIT_BAD_URL=/{print $2}' | tail -n 1)"
if [ -n "$hit" ]; then
  echo "YT_DOCTOR_FAIL: detected bad url ($hit)" >&2
  exit 2
fi

echo "YT_DOCTOR_OK" >&2
