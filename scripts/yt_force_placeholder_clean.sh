#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$DIR/.." && pwd)"
WID_BY_PID="$ROOT/scripts/chrome_wid_by_pid.sh"

MAX_SECONDS="${1:-25}"
INTERVAL="${2:-1}"

PROFILE="/tmp/lucy_yt_force_$(date +%s)"
LOG="/tmp/lucy_yt_force_$(date +%s).log"

URL_OK="https://www.youtube.com/"
URL_BAD="https://pega_aca_la_url/"

CHROME_BIN="$(command -v google-chrome || true)"
if [ -z "$CHROME_BIN" ] && [ -x /opt/google/chrome/chrome ]; then
  CHROME_BIN="/opt/google/chrome/chrome"
fi
if [ -z "$CHROME_BIN" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi

"$CHROME_BIN" \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check \
  --disable-session-crashed-bubble \
  --disable-extensions \
  --new-window "$URL_OK" "$URL_BAD" \
  >"$LOG" 2>&1 &

sleep 1.2

PID=""
while read -r cand; do
  [ -n "$cand" ] || continue
  PID="$cand"
  break
done < <(pgrep -f "chrome.*--user-data-dir=$PROFILE" 2>/dev/null || true)
if [ -z "$PID" ]; then
  echo "ERROR_NO_PID profile=$PROFILE" >&2
  exit 3
fi

wid_out=""
wid_rc=3
WID_HEX=""
while read -r cand; do
  [ -n "$cand" ] || continue
  PID="$cand"
  for _ in $(seq 1 10); do
    set +e
    wid_out="$("$WID_BY_PID" "$PID" 2>/dev/null)"
    wid_rc=$?
    set -e
    if [ "$wid_rc" -eq 0 ]; then
      WID_HEX="$(printf '%s\n' "$wid_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
      if [ -n "$WID_HEX" ]; then
        break 2
      fi
    fi
    sleep 0.3
  done
done < <(pgrep -f "chrome.*--user-data-dir=$PROFILE" 2>/dev/null || true)
if [ -z "$WID_HEX" ]; then
  echo "ERROR_NO_WID pid=$PID profile=$PROFILE" >&2
  exit 3
fi
WID_DEC=$((WID_HEX))

echo "PROFILE=$PROFILE"
echo "PID=$PID"
echo "WID_HEX=$WID_HEX"

xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
sleep 0.2
# Focus the second tab (placeholder) deterministically.
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+2 2>/dev/null || true
sleep 0.2

set +e
out="$("$ROOT/scripts/yt_watch_until_bad_url.sh" "$MAX_SECONDS" "$INTERVAL" "$WID_HEX")"
rc=$?
set -e

echo "$out"
echo "RC=$rc"

hit="$(printf '%s\n' "$out" | awk -F= '/^HIT_BAD_URL=/{print $2}' | tail -n 1)"
outdir="$(printf '%s\n' "$out" | awk -F= '/^OUTDIR=/{print $2}' | tail -n 1)"

if [[ "$rc" -ne 10 ]]; then
  echo "FAIL: expected rc=10 got rc=$rc" >&2
  exit 2
fi
if [[ -z "${hit:-}" || -z "${outdir:-}" ]]; then
  echo "FAIL: missing HIT_BAD_URL or OUTDIR" >&2
  exit 2
fi
if [[ ! -s "$outdir/hit.png" ]]; then
  echo "FAIL: missing $outdir/hit.png" >&2
  exit 2
fi

echo "OK_FORCE_PLACEHOLDER outdir=$outdir hit=$hit"
