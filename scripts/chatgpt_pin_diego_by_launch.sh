#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="${1:-$ROOT/diagnostics/pins/chatgpt_diego.wid}"

PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
EXPECTED_EMAIL="${CHATGPT_EXPECTED_EMAIL:-chatjepetex2025@gmail.com}"

THREAD_URL="${CHATGPT_THREAD_URL:-}"
OPEN_URL="${CHATGPT_OPEN_URL:-https://chatgpt.com/}"
URL="${THREAD_URL:-$OPEN_URL}"

CHROME_BIN="${CHROME_BIN:-/opt/google/chrome/chrome}"
[ -x "$CHROME_BIN" ] || CHROME_BIN="$(command -v google-chrome || true)"
[ -n "${CHROME_BIN:-}" ] || { echo "ERROR_NO_CHROME_BIN" >&2; exit 3; }

# Resolver Profile Dir con email-gate
res="$("$ROOT/scripts/chrome_profile_assert_identity.sh" "$PROFILE_NAME" "$EXPECTED_EMAIL" 2>/dev/null || true)"
PROFILE_DIR="$(printf '%s\n' "$res" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
USER_NAME="$(printf '%s\n' "$res" | awk -F= '/^USER_NAME=/{print $2}' | tail -n 1)"
if [ -z "${PROFILE_DIR:-}" ]; then
  echo "ERROR_PROFILE_RESOLVE" >&2
  printf '%s\n' "$res" >&2
  exit 3
fi

list_chrome_wids() {
  wmctrl -lx 2>/dev/null | awk '/chrome|chromium/{print $1}'
}

list_stack_order() {
  xprop -root _NET_CLIENT_LIST_STACKING 2>/dev/null \
    | sed -n 's/.*# //p' \
    | tr ',' '\n' \
    | awk '{
        gsub(/^[[:space:]]+|[[:space:]]+$/,"");
        if ($0 ~ /^0x[0-9a-fA-F]+$/) print $0
      }' || true
}

mapfile -t pre_wids < <(list_chrome_wids)
declare -A pre_map=()
for w in "${pre_wids[@]}"; do
  pre_map["$w"]=1
done

mkdir -p "$(dirname -- "$PIN_FILE")"

# Lanzar ventana en el perfil correcto (sin depender de ventana activa)
"$CHROME_BIN" \
  --disable-session-crashed-bubble \
  --no-first-run --no-default-browser-check \
  --profile-directory="$PROFILE_DIR" \
  --new-window "$URL" \
  >/tmp/lucy_chatgpt_diego_launch.log 2>&1 || true

# Esperar WID nuevo creado por el launch
WID_HEX=""
for _ in $(seq 1 40); do
  mapfile -t post_wids < <(list_chrome_wids)
  mapfile -t new_wids < <(for w in "${post_wids[@]}"; do
    if [[ -z "${pre_map[$w]:-}" ]]; then
      echo "$w"
    fi
  done)

  if [ "${#new_wids[@]}" -gt 0 ]; then
    declare -A new_map=()
    for w in "${new_wids[@]}"; do
      new_map["$w"]=1
    done
    for w in $(list_stack_order); do
      if [[ -n "${new_map[$w]:-}" ]]; then
        WID_HEX="$w"
      fi
    done
    if [ -z "${WID_HEX:-}" ]; then
      WID_HEX="${new_wids[-1]}"
    fi
    break
  fi
  sleep 0.15
done
[ -n "${WID_HEX:-}" ] || { echo "ERROR_NO_NEW_WID_FROM_LAUNCH profile=$PROFILE_DIR" >&2; exit 3; }

# Validar que existe
xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1 || { echo "ERROR_BADWINDOW $WID_HEX" >&2; exit 3; }

# URL-lock (evita que quede en otra tab)
if [ -x "$ROOT/scripts/chrome_ensure_url_in_window.sh" ]; then
  "$ROOT/scripts/chrome_ensure_url_in_window.sh" "$WID_HEX" "https://chatgpt.com/" 8 >/dev/null 2>&1 || true
fi

TITLE="$(xprop -id "$WID_HEX" _NET_WM_NAME 2>/dev/null | sed -n 's/.*= //p' | tr -d '"')"

{
  echo "WID_HEX=$WID_HEX"
  echo "EMAIL=$USER_NAME"
  echo "PROFILE_DIR=$PROFILE_DIR"
  echo "TITLE=$TITLE"
  echo "TS=$(date +%F_%H%M%S)"
} >"$PIN_FILE"

echo "OK_PIN_DIEGO WID_HEX=$WID_HEX EMAIL=$USER_NAME PIN_FILE=$PIN_FILE"
