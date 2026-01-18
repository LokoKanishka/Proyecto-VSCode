#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$DIR/.." && pwd)"
CAP="$ROOT/scripts/chrome_capture_active_tab.sh"
WID_PROFILE="$ROOT/scripts/chrome_wid_profile_dir.sh"
PROFILE_RESOLVE="$ROOT/scripts/chrome_profile_dir_by_name.sh"

MAX_WINDOWS="${1:-12}"
MAX_TABS="${2:-9}"
OUTROOT="/tmp/lucy_chatgpt_resolve"
mkdir -p "$OUTROOT"
PROFILE_NAME="${CHATGPT_PROFILE_NAME:-}"
PROFILE_DIR_FILTER=""
PIN_FILE="${CHATGPT_WID_PIN_FILE:-}"
if [ -n "${PROFILE_NAME:-}" ]; then
  prof_out="$("$PROFILE_RESOLVE" "$PROFILE_NAME" 2>/dev/null || true)"
  PROFILE_DIR_FILTER="$(printf '%s\n' "$prof_out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
fi

_is_allowed_url() {
  local u_lc
  u_lc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$u_lc" in
    https://chatgpt.com/*|http://chatgpt.com/*) return 0 ;;
    https://www.chatgpt.com/*|http://www.chatgpt.com/*) return 0 ;;
    https://chat.openai.com/*|http://chat.openai.com/*) return 0 ;;
    https://auth.openai.com/*|http://auth.openai.com/*) return 0 ;;
    https://accounts.google.com/*) return 0 ;;
    *) return 1 ;;
  esac
}

mapfile -t wids < <(wmctrl -lx 2>/dev/null | awk '/google-chrome.Google-chrome/ {print $1}' | head -n "$MAX_WINDOWS" || true)
if [ "${#wids[@]}" -eq 0 ]; then
  echo "ERROR_NO_CHROME_WIDS" >&2
  echo "RC=3"
  exit 3
fi

if [ -n "${PIN_FILE:-}" ] && [ -f "$PIN_FILE" ]; then
  pin_wid="$(grep -Eo '0x[0-9a-fA-F]+' "$PIN_FILE" | head -n 1 || true)"
  if [ -n "${pin_wid:-}" ]; then
    set +e
    cap="$($CAP "$pin_wid" 2>/dev/null)"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
      url="$(printf '%s\n' "$cap" | awk -F= '/^URL=/{print $2}' | tail -n 1)"
      title="$(printf '%s\n' "$cap" | awk -F= '/^TITLE=/{print $2}' | tail -n 1)"
      if _is_allowed_url "$url"; then
        echo "WID_HEX=$pin_wid"
        echo "TAB=1"
        echo "TITLE=<<<$title>>>"
        echo "URL=<<<$url>>>"
        echo "RC=0"
        exit 0
      fi
    fi
  fi
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

  if [ -n "${PROFILE_DIR_FILTER:-}" ]; then
    prof_out="$("$WID_PROFILE" "$wid_hex" 2>/dev/null || true)"
    wid_profile="$(printf '%s\n' "$prof_out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
    if [ -n "${wid_profile:-}" ] && [ "$wid_profile" != "Default" ] && [ "$wid_profile" != "$PROFILE_DIR_FILTER" ]; then
      continue
    fi
  fi

  wmctrl -ia "$wid_hex" 2>/dev/null || true
  xdotool windowactivate --sync "$wid_dec" 2>/dev/null || true
  sleep 0.12

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
  echo "ERROR_NO_CHATGPT_URL_IN_ANY_CHROME_WINDOW" >&2
  echo "RC=3"
  exit 3
fi

if [ -n "${PIN_FILE:-}" ]; then
  {
    echo "$best"
    echo "TITLE=$best_title"
  } >"$PIN_FILE" 2>/dev/null || true
fi

echo "WID_HEX=$best"
echo "TAB=$best_tab"
echo "TITLE=<<<$best_title>>>"
echo "URL=<<<$best_url>>>"
echo "RC=0"
