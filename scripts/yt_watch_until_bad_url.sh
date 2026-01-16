#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

MAX_SECONDS="${1:-120}"
INTERVAL="${2:-1}"
OUTROOT="/tmp/lucy_yt_watch"
mkdir -p "$OUTROOT"

start_ts="$(date +%s)"
HIT_BAD_URL=""
SAVED="0"
OUTDIR=""

_is_allowed_host() {
  case "$1" in
    youtube.com|www.youtube.com|m.youtube.com|youtu.be)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

while true; do
  now_ts="$(date +%s)"
  if [ "$((now_ts - start_ts))" -ge "$MAX_SECONDS" ]; then
    break
  fi

  iter_dir="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$"
  "$DIR/yt_doctor_capture_active.sh" "$iter_dir" >/dev/null 2>&1 || true

  url_raw=""
  title_raw=""
  if [ -r "$iter_dir/url.txt" ]; then
    url_raw="$(cat "$iter_dir/url.txt")"
  fi
  if [ -r "$iter_dir/title.txt" ]; then
    title_raw="$(cat "$iter_dir/title.txt")"
  fi

  url_trim="$(printf '%s' "$url_raw" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  url_lc="$(printf '%s' "$url_trim" | tr '[:upper:]' '[:lower:]')"
  title_lc="$(printf '%s' "$title_raw" | tr '[:upper:]' '[:lower:]')"

  reason=""
  if [ -z "$url_trim" ]; then
    reason="empty_url"
  elif [[ "$url_lc" == chrome-error://* || "$url_lc" == chrome://* ]]; then
    reason="chrome_url"
  elif ! printf '%s' "$url_trim" | grep -Eq '^https?://'; then
    reason="bad_scheme"
  elif [[ "$url_lc" == *placeholder* || "$url_lc" == *aca_la_url* || "$url_lc" == *pega* || "$url_lc" == *peg* ]]; then
    reason="placeholder_pattern"
  elif [[ "$title_lc" == *nxdomain* || "$title_lc" == *dns_probe* ]]; then
    reason="title_dns"
  else
    host="$(printf '%s' "$url_trim" | sed -E 's#^[a-zA-Z]+://([^/]+).*#\1#' | tr '[:upper:]' '[:lower:]')"
    if [ -z "$host" ] || ! _is_allowed_host "$host"; then
      reason="host_not_allowed:$host"
    fi
  fi

  if [ -n "$reason" ]; then
    HIT_BAD_URL="$reason"
    SAVED="1"
    OUTDIR="$iter_dir"
    break
  fi

  rm -rf "$iter_dir" 2>/dev/null || true
  sleep "$INTERVAL"
done

echo "HIT_BAD_URL=$HIT_BAD_URL"
echo "SAVED=$SAVED"
echo "OUTDIR=$OUTDIR"

if [ -n "$HIT_BAD_URL" ]; then
  exit 0
fi
exit 1
