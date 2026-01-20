#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# --- LUCY_PIN_LIVE_GUARD_ENTRY: ensure diego pin points to a live WID (avoid BadWindow) ---
PIN_FILE_DEFAULT="$ROOT/diagnostics/pins/chrome_diego.wid"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$PIN_FILE_DEFAULT}"
ENSURE_LIVE="$ROOT/scripts/chrome_diego_pin_ensure_live.sh"
if [ ! -x "$ENSURE_LIVE" ]; then
  echo "ERROR_NO_PIN_ENSURE: $ENSURE_LIVE" >&2
  exit 3
fi
CHROME_DIEGO_PIN_FILE="$PIN_FILE" "$ENSURE_LIVE" "https://chatgpt.com/" >/dev/null
# --- /LUCY_PIN_LIVE_GUARD_ENTRY ---

PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
EXPECTED_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"

GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"
ENSURE_URL="$ROOT/scripts/chrome_ensure_url_in_window.sh"

TARGET_URL="${CHATGPT_TARGET_URL:-https://chatgpt.com/}"

if [ ! -x "$GUARD" ]; then
  echo "ERROR_PREFLIGHT_NO_GUARD $GUARD" >&2
  exit 3
fi

set +e
guard_out="$(CHROME_PROFILE_NAME="$PROFILE_NAME" CHROME_DIEGO_EMAIL="$EXPECTED_EMAIL" CHROME_DIEGO_PIN_FILE="$PIN_FILE" "$GUARD" "$TARGET_URL" 2>&1)"
guard_rc=$?
set -e
if [ "$guard_rc" -ne 0 ]; then
  echo "ERROR_PREFLIGHT_GUARD rc=$guard_rc" >&2
  printf '%s\n' "$guard_out" >&2
  exit 3
fi

WID_HEX="$(printf '%s\n' "$guard_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
EMAIL="$(printf '%s\n' "$guard_out" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"
PROFILE_DIR="$(printf '%s\n' "$guard_out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
TITLE="$(printf '%s\n' "$guard_out" | awk -F= '/^TITLE=/{print $($1=""); sub(/^ /,""); print}' | tail -n 1)"

if [ -z "${WID_HEX:-}" ]; then
  echo "ERROR_PREFLIGHT_NO_WID" >&2
  exit 3
fi
if [ "$EMAIL" != "$EXPECTED_EMAIL" ]; then
  echo "ERROR_PREFLIGHT_EMAIL_MISMATCH got=$EMAIL want=$EXPECTED_EMAIL" >&2
  exit 3
fi
xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1 || { echo "ERROR_PREFLIGHT_BADWINDOW $WID_HEX" >&2; exit 3; }

# URL-lock (evita que esté en WhatsApp/otro chat/tab)
if [ -x "$ENSURE_URL" ]; then
  set +e
  "$ENSURE_URL" "$WID_HEX" "$TARGET_URL" 8 >/dev/null 2>&1
  ensure_rc=$?
  set -e
  if [ "$ensure_rc" -ne 0 ]; then
    echo "ERROR_PREFLIGHT_URL_LOCK rc=$ensure_rc target=$TARGET_URL wid=$WID_HEX" >&2
    exit 3
  fi
fi

echo "WID_HEX=$WID_HEX"
echo "EMAIL=$EMAIL"
echo "PROFILE_DIR=$PROFILE_DIR"
echo "TITLE=$TITLE"
