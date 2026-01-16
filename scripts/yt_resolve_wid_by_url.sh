#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$DIR/.." && pwd)"
CAP="$ROOT/scripts/chrome_capture_active_tab.sh"

MAX_WINDOWS="${1:-12}"
MAX_TABS="${2:-9}"
OUTROOT="/tmp/lucy_yt_resolve"
mkdir -p "$OUTROOT"

_is_allowed_url() {
  local u_lc
  u_lc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$u_lc" in
    https://www.youtube.com/*|http://www.youtube.com/*) return 0 ;;
    https://youtube.com/*|http://youtube.com/*) return 0 ;;
    https://m.youtube.com/*|http://m.youtube.com/*) return 0 ;;
    https://youtu.be/*|http://youtu.be/*) return 0 ;;
    https://consent.youtube.com/*) return 0 ;;
    https://accounts.google.com/*) return 0 ;;
    https://www.google.com/search*|https://google.com/search*) return 0 ;;
    *) return 1 ;;
  esac
}

mapfile -t wids < <(wmctrl -lx 2>/dev/null | awk '/google-chrome.Google-chrome/ {print $1}' | head -n "$MAX_WINDOWS" || true)
if [ "${#wids[@]}" -eq 0 ]; then
  echo "ERROR_NO_CHROME_WIDS" >&2
  exit 3
fi

echo "CANDIDATES=${#wids[@]}" >&2

best=""
best_url=""
best_title=""
best_tab=""

for wid_hex in "${wids[@]}"; do
  wid_dec="$(printf "%d" "$wid_hex" 2>/dev/null || echo 0)"
  if [ "$wid_dec" -le 0 ]; then
    continue
  fi

  # activar ventana para que ctrl+<n> funcione
  wmctrl -ia "$wid_hex" 2>/dev/null || true
  xdotool windowactivate --sync "$wid_dec" 2>/dev/null || true
  sleep 0.12

  # escanear tabs 1..MAX_TABS
  for tab in $(seq 1 "$MAX_TABS"); do
    xdotool key --window "$wid_dec" --clearmodifiers "ctrl+$tab" 2>/dev/null || true
    sleep 0.10

    iter="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$_w${wid_dec}_t${tab}"
    mkdir -p "$iter"

    set +e
    cap="$($CAP "$wid_hex" "$iter" 2>/dev/null)"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
      continue
    fi

    url="$(printf '%s\n' "$cap" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
    title="$(printf '%s\n' "$cap" | awk -F= '/^TITLE=/{print $2}' | tail -n 1)"

    if _is_allowed_url "$url"; then
      best="$wid_hex"
      best_url="$url"
      best_title="$title"
      best_tab="$tab"
      break 2
    fi
  done
done

if [ -z "$best" ]; then
  echo "ERROR_NO_YOUTUBE_URL_IN_ANY_CHROME_WINDOW" >&2
  exit 3
fi

echo "WID_HEX=$best"
echo "TAB=$best_tab"
echo "TITLE=<<<$best_title>>>"
echo "URL=<<<$best_url>>>"
