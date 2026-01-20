#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

CAPTURE="$DIR/chrome_capture_active_tab.sh"

WID_HEX="${1:-}"
TARGET_URL="${2:-}"
MAX_SECONDS="${3:-10}"

if [ -z "${WID_HEX:-}" ] || [ -z "${TARGET_URL:-}" ]; then
  echo "USAGE: yt_ensure_url_in_window.sh <WID_HEX> <target_url> [max_seconds]" >&2
  exit 2
fi
if ! printf '%s' "$TARGET_URL" | grep -Eq '^https?://'; then
  echo "ERROR_BAD_TARGET_URL: <$TARGET_URL>" >&2
  exit 2
fi
if [ ! -x "$CAPTURE" ]; then
  echo "ERROR_NO_CAPTURE: $CAPTURE" >&2
  exit 2
fi

# Navega una vez al target

# --- LUCY_PIN_LIVE_GUARD_YT: if caller passed the pinned WID and it's dead, auto-repin ---
PIN_FILE_DEFAULT="$ROOT/diagnostics/pins/chrome_diego.wid"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$PIN_FILE_DEFAULT}"
ENSURE_LIVE="$ROOT/scripts/chrome_diego_pin_ensure_live.sh"

_read_pin_wid() { awk -F= '/^WID_HEX=/{print $2}' "$PIN_FILE" 2>/dev/null | tail -n 1; }
_is_live() { xprop -id "$1" _NET_WM_NAME >/dev/null 2>&1; }

pin_wid="$(_read_pin_wid || true)"

# Solo auto-repin si el WID muerto que nos pasaron ES el pin actual (evita tocar otras ventanas/WIDs externos)
if [ -n "${WID_HEX:-}" ] && ! _is_live "$WID_HEX" && [ -n "${pin_wid:-}" ] && [ "$pin_wid" = "$WID_HEX" ]; then
  if [ ! -x "$ENSURE_LIVE" ]; then
    echo "ERROR_NO_PIN_ENSURE: $ENSURE_LIVE" >&2
    exit 3
  fi
  echo "PIN_DEAD -> REPIN (yt_ensure)" >&2
  CHROME_DIEGO_PIN_FILE="$PIN_FILE" "$ENSURE_LIVE" "https://chatgpt.com/" >/dev/null
  WID_HEX="$(_read_pin_wid || true)"
  if [ -z "${WID_HEX:-}" ] || ! _is_live "$WID_HEX"; then
    echo "ERROR_REPIN_FAILED (yt_ensure)" >&2
    exit 3
  fi
fi
# --- /LUCY_PIN_LIVE_GUARD_YT ---
WID_DEC=$((WID_HEX))
wmctrl -ia "$WID_HEX" 2>/dev/null || true
xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
sleep 0.15
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+l 2>/dev/null || true
sleep 0.06
xdotool type --window "$WID_DEC" --clearmodifiers --delay 2 "$TARGET_URL" 2>/dev/null || true
xdotool key --window "$WID_DEC" --clearmodifiers Return 2>/dev/null || true
sleep 0.25

OUTROOT="/tmp/lucy_yt_ensure"
mkdir -p "$OUTROOT"
start_ts="$(date +%s)"
last_out=""

want_results=0
case "$TARGET_URL" in
  *"/results?search_query="*) want_results=1 ;;
esac

_is_ok() {
  local url="$1"
  local host path
  host="$(printf '%s' "$url" | sed -E 's#^[a-zA-Z]+://([^/]+).*#\1#' | tr '[:upper:]' '[:lower:]' | sed 's/:.*//')"
  path="$(printf '%s' "$url" | sed -E 's#^[a-zA-Z]+://[^/]+(/[^?]*)?.*#\1#')"

  # toleramos intermedios Google/consent mientras redirige
  case "$host" in
    consent.youtube.com|consent.google.com|accounts.google.com|www.google.com|google.com)
      return 1
      ;;
  esac

  case "$host" in
    youtube.com|www.youtube.com|m.youtube.com|youtu.be)
      if [ "$want_results" -eq 1 ]; then
        [[ "$path" == "/results"* ]] && return 0 || return 1
      fi
      return 0
      ;;
  esac
  return 1
}

while true; do
  now="$(date +%s)"
  if [ "$((now - start_ts))" -ge "$MAX_SECONDS" ]; then
    break
  fi

  iter="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$"
  mkdir -p "$iter"
  last_out="$iter"

  set +e
  cap="$($CAPTURE "$WID_HEX" "$iter" 2>/dev/null)"
  rc=$?
  set -e

  if [ "$rc" -eq 0 ]; then
    url="$(printf '%s\n' "$cap" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
    if [ -n "${url:-}" ] && _is_ok "$url"; then
      echo "OUTDIR=$iter"
      echo "WID_HEX=$WID_HEX"
      echo "URL=$url"
      exit 0
    fi
  fi

  sleep 0.25
done

echo "ERROR_YT_URL_NOT_STABLE target=$TARGET_URL" >&2
[ -n "${last_out:-}" ] && echo "OUTDIR=$last_out"
exit 3
