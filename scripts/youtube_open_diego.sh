#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OPEN_PROFILE="$ROOT/scripts/chrome_open_profile_url.sh"
ENSURE_URL="$ROOT/scripts/yt_ensure_url_in_window.sh"
GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"

URL="${1:-https://www.youtube.com/}"
PROFILE_NAME="${YOUTUBE_PROFILE_NAME:-diego}"
CHROME_DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"

if ! printf '%s' "$URL" | grep -Eq '^https?://'; then
  echo "ERROR_BAD_URL: <$URL>" >&2
  exit 8
fi

host="$(printf '%s' "$URL" | awk -F/ '{print tolower($3)}')"
case "$host" in
  youtube.com|www.youtube.com|m.youtube.com|youtu.be)
    ;;
  *)
    echo "ERROR_BAD_URL: <$URL>" >&2
    exit 8
    ;;
esac

if [ -z "${CHROME_WID_HEX:-}" ] && [ -x "$GUARD" ]; then
  guard_out="$(CHROME_PROFILE_NAME="$PROFILE_NAME" CHROME_DIEGO_EMAIL="$CHROME_DIEGO_EMAIL" "$GUARD" "https://www.google.com/" 2>/dev/null || true)"
  CHROME_WID_HEX="$(printf '%s\n' "$guard_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
  if [ -z "${CHROME_WID_HEX:-}" ]; then
    echo "ERROR_DIEGO_GUARD_NO_WID" >&2
    exit 3
  fi
  export CHROME_WID_HEX
fi

if [ -n "${CHROME_WID_HEX:-}" ] && [ -x "$ENSURE_URL" ]; then
  if "$ENSURE_URL" "$CHROME_WID_HEX" "$URL" 8 >/dev/null 2>&1; then
    echo "OK_OPEN_WID=$CHROME_WID_HEX URL=$URL"
    exit 0
  fi
  echo "ERROR_OPEN_WID URL_LOCK_FAILED wid=$CHROME_WID_HEX" >&2
  exit 3
fi

CHROME_EXTRA_ARGS="--no-first-run --no-default-browser-check --disable-session-crashed-bubble" \
  "$OPEN_PROFILE" "$PROFILE_NAME" "$URL" || true
