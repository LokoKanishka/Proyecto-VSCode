#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"
ENSURE_URL="$ROOT/scripts/chrome_ensure_url_in_window.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"

ITER="${1:-50}"
TARGET_URL="${CHATGPT_TARGET_URL:-https://chatgpt.com/}"
EXPECTED_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"

OUT="/tmp/lucy_stress_diego_client_guard_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"
echo "OUTDIR=$OUT"

fail=0

for i in $(seq 1 "$ITER"); do
  step="$OUT/iter_$(printf '%03d' "$i")"
  mkdir -p "$step"
  echo "== ITER $i ==" | tee -a "$OUT/summary.txt"

  set +e
  guard_out="$("$GUARD" "https://www.google.com/" 2>&1)"
  guard_rc=$?
  set -e
  printf '%s\n' "$guard_out" >"$step/guard.txt"
  if [ "$guard_rc" -ne 0 ]; then
    echo "FAIL: guard_rc=$guard_rc" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi

  WID_HEX="$(printf '%s\n' "$guard_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
  EMAIL="$(printf '%s\n' "$guard_out" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"
  echo "WID_HEX=$WID_HEX" >"$step/meta.txt"
  echo "EMAIL=$EMAIL" >>"$step/meta.txt"

  if [ -z "${WID_HEX:-}" ]; then
    echo "FAIL: no_wid" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi
  if [ "$EMAIL" != "$EXPECTED_EMAIL" ]; then
    echo "FAIL: email_mismatch got=$EMAIL want=$EXPECTED_EMAIL" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi
  if ! xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1; then
    echo "FAIL: badwindow $WID_HEX" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi

  if [ -x "$ENSURE_URL" ]; then
    set +e
    ens_out="$("$ENSURE_URL" "$WID_HEX" "$TARGET_URL" 8 2>&1)"
    ens_rc=$?
    set -e
    printf '%s\n' "$ens_out" >"$step/ensure_url.txt"
    if [ "$ens_rc" -ne 0 ]; then
      echo "FAIL: ensure_url rc=$ens_rc" | tee -a "$OUT/summary.txt"
      fail=1
      break
    fi
  fi

  mkdir -p "$step/capture"
  set +e
  cap_out="$("$CAPTURE" "$WID_HEX" "$step/capture" 2>&1)"
  cap_rc=$?
  set -e
  printf '%s\n' "$cap_out" >"$step/capture/capture.txt"

  url=""
  if [ -r "$step/capture/url.txt" ]; then
    url="$(tr -d '\r' <"$step/capture/url.txt")"
  fi
  echo "URL_CAPTURE=$url" >>"$step/meta.txt"

  if [ -z "${url:-}" ]; then
    echo "FAIL: url_empty" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi
  if ! printf '%s' "$url" | grep -Eq '^https?://'; then
    echo "FAIL: url_bad_format <$url>" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi
  if ! printf '%s' "$url" | grep -Eq '^https?://chatgpt\\.com/'; then
    echo "WARN: url_not_chatgpt <$url>" | tee -a "$OUT/summary.txt"
  fi

  echo "OK: iter=$i wid=$WID_HEX email=$EMAIL" | tee -a "$OUT/summary.txt"
  sleep 0.2
done

if [ "$fail" -eq 0 ]; then
  echo "OK_STRESS_DIEGO_CLIENT_GUARD iters=$ITER outdir=$OUT"
  exit 0
fi

echo "FAIL_STRESS_DIEGO_CLIENT_GUARD outdir=$OUT" >&2
exit 3
