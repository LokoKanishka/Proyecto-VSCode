#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

RESOLVE_PROFILE="$ROOT/scripts/chrome_profile_dir_by_name.sh"
ENSURE_URL="$ROOT/scripts/chrome_ensure_url_in_window.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"
WID_BY_PID="$ROOT/scripts/chrome_wid_by_pid.sh"

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
TARGET_URL="${TARGET_URL:-https://www.youtube.com/}"
OTHER_URL="${OTHER_URL:-https://example.com/}"
OUT="/tmp/lucy_verify_tab_lock_$(date +%Y%m%d_%H%M%S)_$$"
CLASS="lucy-tab-lock-$$"
mkdir -p "$OUT"
echo "OUTDIR=$OUT"

resolve_out="$("$RESOLVE_PROFILE" "$PROFILE_NAME" 2>/dev/null || true)"
PROFILE_DIR="$(printf '%s\n' "$resolve_out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
if [ -z "${PROFILE_DIR:-}" ]; then
  echo "ERROR_NO_PROFILE: <$PROFILE_NAME>" >&2
  exit 3
fi

CHROME_BIN="${CHROME_BIN:-/opt/google/chrome/chrome}"
if [ ! -x "$CHROME_BIN" ]; then
  CHROME_BIN="$(command -v google-chrome || true)"
fi
if [ -z "${CHROME_BIN:-}" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi

"$CHROME_BIN" --class="$CLASS" --profile-directory="$PROFILE_DIR" --new-window "$OTHER_URL" "$TARGET_URL" \
  >/tmp/lucy_verify_tab_lock.log 2>&1 &
CHROME_PID="$!"
sleep 1.2

WID_HEX=""
for _ in $(seq 1 10); do
  stack="$(xprop -root _NET_CLIENT_LIST_STACKING 2>/dev/null | sed -n 's/.*# //p' | tr ',' '\n' | tr -d ' ')"
  while read -r wid; do
    [ -n "${wid:-}" ] || continue
    if wmctrl -lx 2>/dev/null | awk -v w="$wid" '$1==w && $3 ~ /google-chrome/ {found=1} END{exit !found}'; then
      WID_HEX="$wid"
      break
    fi
  done < <(printf '%s\n' "$stack" | awk 'NF{list[NR]=$0} END{for(i=NR;i>=1;i--) print list[i]}')
  if [ -n "${WID_HEX:-}" ]; then
    break
  fi
  sleep 0.3
done

if [ -z "${WID_HEX:-}" ]; then
  echo "ERROR_NO_WID" >&2
  exit 3
fi

WID_DEC=$((WID_HEX))
wmctrl -ia "$WID_HEX" 2>/dev/null || true
xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
sleep 0.2
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+1 2>/dev/null || true
sleep 0.2

set +e
ensure_out="$("$ENSURE_URL" "$WID_HEX" "$TARGET_URL" 8 2>&1)"
ensure_rc=$?
set -e
printf '%s\n' "$ensure_out" >"$OUT/ensure_url.txt"
if [ "$ensure_rc" -ne 0 ]; then
  echo "ERROR_ENSURE_URL rc=$ensure_rc (see $OUT/ensure_url.txt)" >&2
  exit 3
fi

mkdir -p "$OUT/capture"
"$CAPTURE" "$WID_HEX" "$OUT/capture" >"$OUT/capture/capture.txt" 2>&1 || true

url="$(cat "$OUT/capture/url.txt" 2>/dev/null || true)"
if [[ "$url" != "$TARGET_URL"* ]]; then
  echo "ERROR_URL_MISMATCH: <$url>" >&2
  exit 3
fi

echo "OK_VERIFY_TAB_LOCK outdir=$OUT wid=$WID_HEX"
