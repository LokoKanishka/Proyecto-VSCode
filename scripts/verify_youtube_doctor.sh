#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

missing=0
for bin in xdotool; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "MISSING_DEP: $bin" >&2
    missing=1
  fi
done

if ! command -v xclip >/dev/null 2>&1 && ! command -v xsel >/dev/null 2>&1; then
  echo "MISSING_DEP: xclip or xsel" >&2
  missing=1
fi

if ! command -v import >/dev/null 2>&1; then
  echo "MISSING_DEP: import (ImageMagick)" >&2
  missing=1
fi

if [ "$missing" -ne 0 ]; then
  exit 2
fi

echo "[YT-DOCTOR] Running unit tests..." >&2
python3 -m unittest -q tests.test_yt_doctor_rules

echo "[YT-DOCTOR] Launching clean Chrome..." >&2
"$DIR/youtube_open_clean.sh" "https://www.youtube.com/" >/dev/null 2>&1 || true
sleep 2

wid="$(xdotool search --onlyvisible --class 'google-chrome' 2>/dev/null | tail -n 1 || true)"
if [ -z "$wid" ]; then
  echo "YT_DOCTOR_FAIL: could not resolve Chrome window" >&2
  exit 2
fi
xdotool windowactivate --sync "$wid" 2>/dev/null || true
sleep 0.2

echo "[YT-DOCTOR] Capture smoke..." >&2
capture="$($DIR/chrome_capture_active_tab.sh "$(printf '0x%08x' "$wid")" 2>/dev/null || true)"
url="$(printf '%s' "$capture" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
if ! printf '%s' "$url" | grep -Eq '^https?://'; then
  echo "YT_DOCTOR_FAIL: capture URL invalid <$url>" >&2
  exit 2
fi

echo "[YT-DOCTOR] Watching for BAD_URL (25s)..." >&2
set +e
output="$($DIR/yt_watch_until_bad_url.sh 25 1 "$(printf '0x%08x' "$wid")")"
rc=$?
set -e
echo "$output"

if [ "$rc" -eq 11 ]; then
  echo "YT_DOCTOR_FAIL: unreliable clipboard (empty url)" >&2
  exit 2
fi
if [ "$rc" -eq 3 ]; then
  echo "YT_DOCTOR_FAIL: could not resolve WID" >&2
  exit 2
fi
if [ "$rc" -eq 10 ]; then
  hit="$(printf '%s' "$output" | awk -F= '/^HIT_BAD_URL=/{print $2}' | tail -n 1)"
  echo "YT_DOCTOR_FAIL: detected bad url ($hit)" >&2
  exit 2
fi

echo "YT_DOCTOR_OK" >&2
