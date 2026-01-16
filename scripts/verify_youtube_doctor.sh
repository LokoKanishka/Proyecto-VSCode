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

echo "[YT-DOCTOR] Placeholder deterministic test..." >&2
set +e
force_out="$($DIR/yt_force_placeholder_clean.sh 12 1)"
force_rc=$?
set -e
echo "$force_out"
if [ "$force_rc" -ne 0 ]; then
  echo "YT_DOCTOR_FAIL: placeholder test rc=$force_rc" >&2
  exit 2
fi
if ! printf '%s' "$force_out" | grep -q "OK_FORCE_PLACEHOLDER"; then
  echo "YT_DOCTOR_FAIL: placeholder test missing OK" >&2
  exit 2
fi

echo "[YT-DOCTOR] Launching clean Chrome..." >&2
open_url="https://www.youtube.com/"
set +e
open_out="$($DIR/youtube_open_clean.sh "$open_url" 2>/dev/null)"
open_rc=$?
set -e
if [ "$open_rc" -ne 0 ]; then
  echo "YT_DOCTOR_FAIL: youtube_open_clean rc=$open_rc" >&2
  exit 2
fi
pid="$(printf '%s\n' "$open_out" | awk -F= '/^PID=/{print $2}' | tail -n 1)"
profile_dir="$(printf '%s\n' "$open_out" | awk -F= '/^OPENED_PROFILE_DIR=/{print $2}' | tail -n 1)"
if [ -z "$pid" ]; then
  echo "YT_DOCTOR_FAIL: missing PID from youtube_open_clean" >&2
  exit 2
fi
sleep 2

wid_out=""
wid_rc=3
wid_hex=""
pid_candidates=("$pid")
if [ -n "$profile_dir" ]; then
  while read -r cand; do
    [ -n "$cand" ] && pid_candidates+=("$cand")
  done < <(pgrep -f "chrome.*--user-data-dir=$profile_dir" 2>/dev/null || true)
fi

for cand in "${pid_candidates[@]}"; do
  for _ in $(seq 1 10); do
    set +e
    wid_out="$($DIR/chrome_wid_by_pid.sh "$cand" 2>/dev/null)"
    wid_rc=$?
    set -e
    if [ "$wid_rc" -eq 0 ]; then
      wid_hex="$(printf '%s\n' "$wid_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
      if [ -n "$wid_hex" ]; then
        break 2
      fi
    fi
    sleep 0.3
  done
done
if [ -z "$wid_hex" ]; then
  echo "YT_DOCTOR_FAIL: could not resolve WID from PID" >&2
  exit 2
fi
if [ -z "$wid_hex" ]; then
  echo "YT_DOCTOR_FAIL: missing WID_HEX" >&2
  exit 2
fi
wid_dec=$((wid_hex))
xdotool windowactivate --sync "$wid_dec" 2>/dev/null || true
sleep 0.2
xdotool key --window "$wid_dec" --clearmodifiers ctrl+1 2>/dev/null || true
sleep 0.2

echo "[YT-DOCTOR] Capture smoke..." >&2
set +e
capture="$($DIR/chrome_capture_active_tab.sh "$wid_hex" 2>/dev/null)"
cap_rc=$?
set -e
if [ "$cap_rc" -eq 11 ]; then
  echo "YT_DOCTOR_FAIL: capture URL invalid" >&2
  exit 2
fi
if [ "$cap_rc" -ne 0 ]; then
  echo "YT_DOCTOR_FAIL: capture rc=$cap_rc" >&2
  exit 2
fi
url="$(printf '%s' "$capture" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
if ! printf '%s' "$url" | grep -Eq '^https?://'; then
  echo "YT_DOCTOR_FAIL: capture URL invalid <$url>" >&2
  exit 2
fi

echo "[YT-DOCTOR] Watching for BAD_URL (25s)..." >&2
set +e
output="$($DIR/yt_watch_until_bad_url.sh 25 1 "$wid_hex")"
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
if [ "$rc" -ne 0 ]; then
  echo "YT_DOCTOR_FAIL: unexpected watcher rc=$rc" >&2
  exit 2
fi

echo "YT_DOCTOR_OK" >&2
