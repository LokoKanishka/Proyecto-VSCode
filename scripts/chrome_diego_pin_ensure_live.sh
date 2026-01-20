#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

START_URL="${1:-https://chatgpt.com/}"

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
EXPECT_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
MAX_SECONDS="${CHROME_PIN_ENSURE_MAX_SECONDS:-15}"

GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR_MISSING_TOOL: $1" >&2; exit 3; }; }
need awk
need xprop

mkdir -p "$(dirname "$PIN_FILE")"

_pin_wid() {
  awk -F= '/^WID_HEX=/{print $2}' "$PIN_FILE" 2>/dev/null | tail -n 1 || true
}

_is_live() {
  local wid="$1"
  [ -n "${wid:-}" ] || return 1
  xprop -id "$wid" _NET_WM_NAME >/dev/null 2>&1
}

_repin() {
  if [ ! -x "$GUARD" ]; then
    echo "ERROR_NO_GUARD: $GUARD" >&2
    exit 3
  fi
  CHROME_PROFILE_NAME="$PROFILE_NAME" CHROME_DIEGO_EMAIL="$EXPECT_EMAIL" \
    "$GUARD" "$START_URL" >/dev/null
}

wid="$(_pin_wid)"
if _is_live "$wid"; then
  echo "OK_PIN_ALIVE WID_HEX=$wid EMAIL=$EXPECT_EMAIL PIN_FILE=$PIN_FILE"
  exit 0
fi

echo "PIN_DEAD -> REPIN" >&2
_repin

wid="$(_pin_wid)"
if _is_live "$wid"; then
  echo "OK_REPIN WID_HEX=$wid EMAIL=$EXPECT_EMAIL PIN_FILE=$PIN_FILE START_URL=$START_URL"
  exit 0
fi

echo "ERROR_REPIN_FAILED PIN_FILE=$PIN_FILE WID_HEX=${wid:-<none>}" >&2
exit 3
