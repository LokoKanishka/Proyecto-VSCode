#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RESOLVER="$ROOT/scripts/chrome_profile_dir_by_name.sh"

NAME_OR_DIR="${1:-}"
URL="${2:-}"

if [ -z "${NAME_OR_DIR:-}" ] || [ -z "${URL:-}" ]; then
  echo "USAGE: chrome_open_profile_url.sh <profile_name_or_dir> <https://url>" >&2
  exit 2
fi

if ! printf '%s' "$URL" | grep -Eq '^https?://'; then
  echo "ERROR_BAD_URL: <$URL>" >&2
  exit 2
fi

PROFILE_DIR="$NAME_OR_DIR"
BASE_LINE=""

if [[ "$NAME_OR_DIR" != Profile* && "$NAME_OR_DIR" != Default && "$NAME_OR_DIR" != "System Profile" ]]; then
  out="$("$RESOLVER" "$NAME_OR_DIR" 2>/dev/null || true)"
  PROFILE_DIR="$(printf '%s\n' "$out" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1 | tr -d '\r')"
  BASE_LINE="$(printf '%s\n' "$out" | awk -F= '/^BASE=/{print $2}' | tail -n 1)"
  if [ -z "${PROFILE_DIR:-}" ]; then
    echo "ERROR_NO_PROFILE: <$NAME_OR_DIR>" >&2
    exit 3
  fi
fi

CHROME_BIN="${CHROME_BIN:-/opt/google/chrome/chrome}"
if [ ! -x "$CHROME_BIN" ]; then
  CHROME_BIN="$(command -v google-chrome || true)"
fi
if [ -z "${CHROME_BIN:-}" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi

extra_args=()
if [ -n "${CHROME_CLASS:-}" ]; then
  extra_args+=(--class="$CHROME_CLASS")
fi
if [ -n "${CHROME_EXTRA_ARGS:-}" ]; then
  # Allow caller to pass raw args (space-separated).
  # shellcheck disable=SC2206
  extra_args+=($CHROME_EXTRA_ARGS)
fi

"$CHROME_BIN" --profile-directory="$PROFILE_DIR" --new-window "${extra_args[@]}" "$URL" \
  >/tmp/lucy_chrome_open_profile.log 2>&1 & disown || true
echo "OK_OPEN profile_dir=$PROFILE_DIR url=$URL base=${BASE_LINE:-unknown}"
