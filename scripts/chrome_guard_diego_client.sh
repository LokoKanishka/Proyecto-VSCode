#!/bin/bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# A29: recursion marker (do not call chrome_diego_pin_ensure_live from inside guard)
export LUCY_GUARD_RUNNING="1"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

# A34 - Diego Chrome Guard Client (PASSIVE BEACON STRATEGY)
# Safety: do not send input to any window until it is identified by beacon token.

TARGET_URL="${1:-https://www.google.com/}"
MAX_SECONDS="${CHROME_GUARD_MAX_SECONDS:-20}"
TARGET_MAX_SECONDS="${CHROME_GUARD_TARGET_MAX_SECONDS:-$MAX_SECONDS}"

REQUIRED_PROFILE_DIR="Profile 1"
REQUIRED_EMAIL="chatjepetex2025@gmail.com"

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR_MISSING_TOOL: $1" >&2; exit 3; }; }
need wmctrl
need xdotool

CHROME_BIN="${CHROME_BIN:-/opt/google/chrome/chrome}"
if [ ! -x "$CHROME_BIN" ]; then
  CHROME_BIN="$(command -v google-chrome || true)"
fi
if [ -z "${CHROME_BIN:-}" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
profile_norm="${PROFILE_NAME,,}"
if [ "$profile_norm" != "diego" ]; then
  echo "ERROR_BAD_PROFILE_NAME expected=diego got=$PROFILE_NAME" >&2
  exit 3
fi

EXPECT_EMAIL="${CHROME_DIEGO_EMAIL:-$REQUIRED_EMAIL}"
if [ "$EXPECT_EMAIL" != "$REQUIRED_EMAIL" ]; then
  echo "ERROR_BAD_EXPECT_EMAIL expected=$REQUIRED_EMAIL got=$EXPECT_EMAIL" >&2
  exit 3
fi

PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
LOG="/tmp/lucy_chrome_guard_diego.log"
CAP="$ROOT/scripts/chrome_capture_active_tab.sh"
if [ ! -x "$CAP" ]; then
  CAP="$ROOT/scripts/chrome_capture_url_omnibox.sh"
fi
if [ ! -x "$CAP" ]; then
  echo "ERROR_NO_CAP_TOOL: $CAP" >&2
  exit 3
fi

TOKEN="LUCY_BEACON_$(date +%s)_$$"
BEACON_URL="https://www.google.com/search?q=${TOKEN}"

OUTROOT="/tmp/lucy_guard_scan/${TOKEN}"
mkdir -p "$OUTROOT/target"
mkdir -p "$(dirname "$PIN_FILE")"
: >"$LOG"

log() { echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"; }

if ! printf '%s' "$TARGET_URL" | grep -Eq '^https?://'; then
  echo "ERROR_BAD_TARGET_URL: <$TARGET_URL>" >&2
  exit 2
fi

navigate_url() {
  local wid_hex="$1"
  local url="$2"
  local wid_dec=$((wid_hex))

  log "Action: Navigating Verified WID=$wid_hex"

  wmctrl -ia "$wid_hex" 2>/dev/null || true
  xdotool windowactivate --sync "$wid_dec" 2>/dev/null || true
  sleep 0.2
  xdotool key --window "$wid_dec" --clearmodifiers Escape 2>/dev/null || true
  sleep 0.1
  xdotool key --window "$wid_dec" --clearmodifiers ctrl+l 2>/dev/null || true
  sleep 0.1
  xdotool type --window "$wid_dec" --clearmodifiers --delay 2 "$url" 2>/dev/null || true
  xdotool key --window "$wid_dec" --clearmodifiers Return 2>/dev/null || true
  sleep 0.5
}

found_wid=""

# Try to reuse pin if still alive (passive check only).
if [ -s "$PIN_FILE" ]; then
  pin_wid="$(awk -F= '/^WID_HEX=/{print $2}' "$PIN_FILE" | tail -n 1)"
  if [ -n "${pin_wid:-}" ]; then
    if wmctrl -l | awk '{print $1}' | grep -qx "$pin_wid"; then
      log "Strategy: Reusing live PIN WID=$pin_wid"
      found_wid="$pin_wid"
    else
      log "PIN stale: WID not found"
    fi
  fi
fi

if [ -z "$found_wid" ]; then
  log "Strategy: Launching BEACON ($TOKEN)"

  "$CHROME_BIN" \
    --profile-directory="$REQUIRED_PROFILE_DIR" \
    --new-window \
    "$BEACON_URL" >>"$LOG" 2>&1 &

  log "Scan: Waiting for window title containing '$TOKEN'..."
  scan_deadline=$(( $(date +%s) + 10 ))
  while [ "$(date +%s)" -lt "$scan_deadline" ]; do
    match_line="$(wmctrl -l | grep "$TOKEN" | head -n 1 || true)"
    if [ -n "$match_line" ]; then
      found_wid="$(printf '%s\n' "$match_line" | awk '{print $1}')"
      log "MATCH: Found Beacon in WID=$found_wid"
      break
    fi
    sleep 0.5
  done
fi

if [ -z "$found_wid" ]; then
  echo "ERROR_GUARD_FAILED: No window appeared with token '$TOKEN' in title." >&2
  exit 3
fi

navigate_url "$found_wid" "$TARGET_URL"

final_url=""
final_title=""
deadline=$(( $(date +%s) + TARGET_MAX_SECONDS ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  iter="$OUTROOT/target/$(date +%Y%m%d_%H%M%S)_$$"
  mkdir -p "$iter"

  "$CAP" "$found_wid" "$iter" >/dev/null 2>&1 || true

  if [ -r "$iter/url.txt" ]; then
    u="$(head -n 1 "$iter/url.txt" | sed 's/^<<<//;s/>>>$//')"
    t="$(head -n 1 "$iter/title.txt" 2>/dev/null || true)"
    check_stub="${TARGET_URL:0:15}"
    if [[ "$u" == "$check_stub"* ]]; then
      final_url="$u"
      final_title="$t"
      break
    fi
  fi
  sleep 0.5
done

if [[ "$found_wid" != 0x* ]]; then
  found_wid=$(printf "0x%x" $((found_wid)))
fi

{
  echo "WID_HEX=$found_wid"
  echo "EMAIL=$REQUIRED_EMAIL"
  echo "PROFILE_DIR=$REQUIRED_PROFILE_DIR"
  printf 'TITLE="%s"\n' "$(printf '%s' "$final_title" | sed 's/"/\\"/g')"
  echo "TS=$(date +%Y-%m-%d_%H%M%S)"
} > "$PIN_FILE"

echo "OK_GUARD_DIEGO_CLIENT"
echo "WID_HEX=$found_wid"
echo "EMAIL=$REQUIRED_EMAIL"
echo "PROFILE_DIR=$REQUIRED_PROFILE_DIR"
echo "PIN_FILE=$PIN_FILE"
echo "SCAN_DIR=$OUTROOT"
echo "URL=${final_url:-}"
exit 0
