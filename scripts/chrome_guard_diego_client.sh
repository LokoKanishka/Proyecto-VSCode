#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"

TARGET_URL="${1:-https://www.google.com/}"
EXPECTED_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
MAX_TRIES="${CHROME_DIEGO_MAX_TRIES:-3}"

mkdir -p "$(dirname -- "$PIN_FILE")"

# Detect chrome config dir (prefer google-chrome)
CHROME_CFG="${CHROME_CFG:-$HOME/.config/google-chrome}"
LOCAL_STATE="$CHROME_CFG/Local State"
if [ ! -r "$LOCAL_STATE" ]; then
  echo "ERROR_NO_LOCAL_STATE: $LOCAL_STATE" >&2
  exit 3
fi

detect_chrome_bin() {
  if [ -x "/opt/google/chrome/chrome" ]; then
    echo "/opt/google/chrome/chrome"
    return
  fi
  command -v google-chrome || true
}

resolve_profile_dir_and_email() {
  python3 - <<'PY'
from pathlib import Path
import json, os, sys

local_state = Path(os.environ["LOCAL_STATE"])
profile_name = os.environ["PROFILE_NAME"]
expected = os.environ["EXPECTED_EMAIL"]

data = json.loads(local_state.read_text(encoding="utf-8", errors="ignore"))
info = (((data.get("profile") or {}).get("info_cache")) or {})

best_dir = ""
best_email = ""
for prof_dir, meta in info.items():
    name = (meta or {}).get("name") or ""
    email = (meta or {}).get("user_name") or ""
    if str(name).strip().lower() == profile_name.strip().lower():
        best_dir = prof_dir
        best_email = email
        break

if not best_dir:
    print("ERROR_NO_PROFILE_MATCH")
    sys.exit(10)

print(f"PROFILE_DIR={best_dir}")
print(f"EMAIL={best_email}")

if expected and best_email and best_email.strip().lower() != expected.strip().lower():
    print(f"ERROR_EMAIL_MISMATCH expected={expected} got={best_email}")
    sys.exit(11)
PY
}

list_chrome_wids() {
  wmctrl -lx 2>/dev/null | awk '$3 ~ /google-chrome/ {print $1}' | sed '/^$/d' | sort -u || true
}

topmost_from_set() {
  local stack
  stack="$(xprop -root _NET_CLIENT_LIST_STACKING 2>/dev/null | sed -n 's/.*# //p' | tr ',' '\n' | tr -d ' ' | sed '/^$/d' || true)"
  if [ -z "$stack" ]; then
    tail -n 1
    return
  fi
  awk '
    NR==FNR {cand[$1]=1; last=$1; next}
    { if (cand[$1]) pick=$1 }
    END { if (pick) print pick; else if (last) print last; }
  ' /dev/stdin <(printf '%s\n' "$stack")
}

export LOCAL_STATE PROFILE_NAME EXPECTED_EMAIL

PROFILE_DIR=""
EMAIL=""

CHROME_BIN="$(detect_chrome_bin)"
if [ -z "${CHROME_BIN:-}" ]; then
  echo "ERROR_NO_CHROME_BIN" >&2
  exit 3
fi

tries=0
while [ "$tries" -lt "$MAX_TRIES" ]; do
  tries=$((tries + 1))

  res="$(resolve_profile_dir_and_email 2>/dev/null || true)"
  PROFILE_DIR="$(printf '%s\n' "$res" | awk -F= '/^PROFILE_DIR=/{print $2}' | tail -n 1)"
  EMAIL="$(printf '%s\n' "$res" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"

  if printf '%s' "$res" | grep -q "ERROR_EMAIL_MISMATCH"; then
    echo "ERROR_EMAIL_MISMATCH (Local State) expected=$EXPECTED_EMAIL got=$EMAIL" >&2
    if [ "$tries" -ge "$MAX_TRIES" ]; then
      exit 3
    fi
  elif [ -z "${PROFILE_DIR:-}" ]; then
    echo "ERROR_NO_PROFILE_DIR (Local State) name=$PROFILE_NAME" >&2
    exit 3
  elif [ -z "${EMAIL:-}" ]; then
    echo "ERROR_NO_EMAIL (Local State) profile_dir=$PROFILE_DIR" >&2
    exit 3
  fi

  BEFORE="$(list_chrome_wids)"

  "$CHROME_BIN" --profile-directory="$PROFILE_DIR" --new-window "$TARGET_URL" \
    >/tmp/lucy_chrome_guard_diego.log 2>&1 &
  LAUNCH_PID="$!"
  sleep 0.7

  WID_HEX=""
  for _ in $(seq 1 30); do
    AFTER="$(list_chrome_wids)"
    NEW="$(comm -13 <(printf '%s\n' "$BEFORE" | sort -u) <(printf '%s\n' "$AFTER" | sort -u) || true)"
    if [ -n "$NEW" ]; then
      WID_HEX="$(printf '%s\n' "$NEW" | topmost_from_set | tail -n 1)"
      if [ -n "${WID_HEX:-}" ]; then
        break
      fi
    fi

    mapfile -t pids < <(printf '%s\n' "$LAUNCH_PID" && pgrep -P "$LAUNCH_PID" 2>/dev/null || true)
    if [ "${#pids[@]}" -gt 0 ]; then
      wid_pid="$(wmctrl -lp 2>/dev/null | awk -v pids="$(printf '%s,' "${pids[@]}")" '
        BEGIN { split(pids,a,","); for(i in a) if(a[i]!="") wanted[a[i]]=1; }
        { if ($3 in wanted) wid=$1; }
        END { if (wid!="") print wid; }
      ')"
      if [ -n "${wid_pid:-}" ]; then
        WID_HEX="$wid_pid"
        break
      fi
    fi

    sleep 0.2
  done

  if [ -z "${WID_HEX:-}" ]; then
    echo "ERROR_NO_WID_AFTER_LAUNCH (delta+stacking+pid failed) see /tmp/lucy_chrome_guard_diego.log" >&2
    exit 3
  fi

  if ! xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1; then
    echo "ERROR_BADWINDOW $WID_HEX" >&2
    exit 3
  fi

  if [ -n "${EMAIL:-}" ] && [ "$EMAIL" != "$EXPECTED_EMAIL" ]; then
    wmctrl -ic "$WID_HEX" 2>/dev/null || true
    if [ "$tries" -ge "$MAX_TRIES" ]; then
      echo "ERROR_EMAIL_MISMATCH (after launch) expected=$EXPECTED_EMAIL got=$EMAIL" >&2
      exit 3
    fi
    continue
  fi

  TITLE="$(xprop -id "$WID_HEX" _NET_WM_NAME 2>/dev/null | sed -n 's/.*= //p' | tr -d '\r' | tail -n 1 || true)"
  {
    echo "WID_HEX=$WID_HEX"
    echo "EMAIL=$EMAIL"
    echo "PROFILE_DIR=$PROFILE_DIR"
    echo "TITLE=$TITLE"
    echo "TS=$(date +%F_%H%M%S)"
  } > "$PIN_FILE"

  echo "OK_GUARD_DIEGO_CLIENT"
  echo "WID_HEX=$WID_HEX"
  echo "EMAIL=$EMAIL"
  echo "PROFILE_DIR=$PROFILE_DIR"
  echo "PIN_FILE=$PIN_FILE"
  exit 0
done

echo "ERROR_GUARD_DIEGO_CLIENT_FAIL" >&2
exit 3
