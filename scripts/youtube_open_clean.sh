#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%s)"
URL="${1:-}"
PROFILE_DIR="${PROFILE_DIR:-/tmp/lucy_yt_clean_${STAMP}}"

_normalize_host() {
  local raw="$1"
  printf '%s' "$raw" | tr '[:upper:]' '[:lower:]'
}

_extract_host() {
  local raw="$1"
  printf '%s' "$raw" | sed -E 's#^[a-zA-Z]+://([^/]+).*#\1#'
}

_is_allowed_host() {
  local host="$(_normalize_host "$1")"
  case "$host" in
    youtube.com|www.youtube.com|m.youtube.com|youtu.be)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if [ -n "$URL" ]; then
  if ! printf '%s' "$URL" | grep -Eq '^https?://'; then
    echo "ERROR_BAD_URL: <$URL>" >&2
    exit 8
  fi
  host="$(_extract_host "$URL")"
  if [ -z "$host" ] || ! _is_allowed_host "$host"; then
    echo "ERROR_BAD_URL: <$URL>" >&2
    exit 8
  fi
else
  URL="https://www.youtube.com/"
fi

google-chrome \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-session-crashed-bubble \
  --disable-extensions \
  --new-window "$URL" \
  >/tmp/lucy_youtube_clean_chrome.log 2>&1 &

echo "OPENED_PROFILE_DIR=$PROFILE_DIR"
echo "LOG=/tmp/lucy_youtube_clean_chrome.log"
