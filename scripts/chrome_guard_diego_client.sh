#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

START_URL="${1:-https://www.google.com/}"
MAX_SECONDS="${CHROME_GUARD_MAX_SECONDS:-12}"

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
EXPECT_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"

RESOLVER="$ROOT/scripts/chrome_profile_dir_by_name.sh"
CAP="$ROOT/scripts/chrome_capture_active_tab.sh"

CHROME_BIN="${CHROME_BIN:-/opt/google/chrome/chrome}"
if [ ! -x "$CHROME_BIN" ]; then
  CHROME_BIN="$(command -v google-chrome || true)"
fi
if [ -z "${CHROME_BIN:-}" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi
if [ ! -x "$CAP" ]; then
  echo "ERROR_NO_CAP_TOOL: $CAP" >&2
  exit 3
fi

PROFILE_DIR=""
if [ -x "$RESOLVER" ]; then
  out="$($RESOLVER "$PROFILE_NAME" 2>/dev/null || true)"
  PROFILE_DIR="$(printf '%s\n' "$out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
fi
if [ -z "${PROFILE_DIR:-}" ]; then
  # fallback razonable si el resolver no está/rompe
  PROFILE_DIR="Profile 1"
fi

TOKEN="$(date +%s)_$$"
if [[ "$START_URL" == *"?"* ]]; then
  GUARD_URL="${START_URL}&lucy_guard=${TOKEN}"
else
  GUARD_URL="${START_URL}?lucy_guard=${TOKEN}"
fi

LOG="/tmp/lucy_chrome_guard_diego.log"
OUTROOT="/tmp/lucy_guard_scan/${TOKEN}"
mkdir -p "$OUTROOT/all"

# Siempre pedimos ventana nueva (aunque Chrome use sesión existente del mismo perfil)
"$CHROME_BIN" --profile-directory="$PROFILE_DIR" --new-window "$GUARD_URL" >>"$LOG" 2>&1 || true

deadline=$(( $(date +%s) + MAX_SECONDS ))
found_wid=""
found_url=""
found_title=""

while [ "$(date +%s)" -lt "$deadline" ]; do
  # listar ventanas Chrome
  mapfile -t wids < <(wmctrl -lx 2>/dev/null | awk '$3 ~ /google-chrome/ {print $1}' | awk 'NF' || true)

  for wid in "${wids[@]}"; do
    d="$OUTROOT/all/$wid"
    mkdir -p "$d"

    set +e
    "$CAP" "$wid" "$d" >/dev/null 2>&1
    rc=$?
    set -e
    [ "$rc" -eq 0 ] || continue

    url=""
    if [ -r "$d/url.txt" ]; then
      url="$(head -n 1 "$d/url.txt" | sed 's/^<<<//;s/>>>$//')"
    fi
    title=""
    if [ -r "$d/title.txt" ]; then
      title="$(head -n 1 "$d/title.txt")"
    fi

    if printf '%s' "$url" | grep -q "lucy_guard=${TOKEN}"; then
      found_wid="$wid"
      found_url="$url"
      found_title="$title"
      break
    fi
  done

  if [ -n "${found_wid:-}" ]; then
    break
  fi
  sleep 0.25
done

if [ -z "${found_wid:-}" ]; then
  echo "ERROR_GUARD_FAILED profile=$PROFILE_NAME email=$EXPECT_EMAIL (no_token_seen)" >&2
  echo "SEE_LOG=$LOG" >&2
  echo "SEE_SCAN=$OUTROOT" >&2
  echo "URLS_CAPTURED(head):" >&2
  (find "$OUTROOT/all" -maxdepth 2 -name url.txt -print -exec sh -lc 'head -n 1 "$1" 2>/dev/null || true' _ {} \; | head -n 40) >&2 || true
  exit 3
fi

mkdir -p "$(dirname "$PIN_FILE")"
ts="$(date +%F_%H%M%S)"
{
  echo "WID_HEX=$found_wid"
  echo "EMAIL=$EXPECT_EMAIL"
  echo "PROFILE_DIR=$PROFILE_DIR"
  printf 'TITLE="%s"\n' "$(printf '%s' "$found_title" | sed 's/"/\\"/g')"
  echo "TS=$ts"
} >"$PIN_FILE"

echo "OK_GUARD_DIEGO_CLIENT"
echo "WID_HEX=$found_wid"
echo "EMAIL=$EXPECT_EMAIL"
echo "PROFILE_DIR=$PROFILE_DIR"
echo "PIN_FILE=$PIN_FILE"
echo "SCAN_DIR=$OUTROOT"
echo "URL=$found_url"
