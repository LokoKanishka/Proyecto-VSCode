#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

PIN_FILE="${CHATGPT_WID_PIN_FILE:-$ROOT/diagnostics/pins/chatgpt_diego.wid}"
PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
EXPECTED_EMAIL="${CHATGPT_EXPECTED_EMAIL:-chatjepetex2025@gmail.com}"
ITER="${1:-40}"

PINNER="$ROOT/scripts/chatgpt_pin_diego_by_launch.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"
ENSURE_URL="$ROOT/scripts/chrome_ensure_url_in_window.sh"
GET_URL="$ROOT/scripts/chatgpt_get_url_x11.sh"

OUT="/tmp/lucy_stress_diego_gate_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"
echo "OUTDIR=$OUT"

fail=0

for i in $(seq 1 "$ITER"); do
  step="$OUT/iter_$(printf '%03d' "$i")"
  mkdir -p "$step"

  echo "== ITER $i ==" | tee -a "$OUT/summary.txt"

  # 1) Repin determinístico (launch + email gate + class)
  set +e
  pin_out="$(CHATGPT_PROFILE_NAME="$PROFILE_NAME" CHATGPT_EXPECTED_EMAIL="$EXPECTED_EMAIL" "$PINNER" "$PIN_FILE" 2>&1)"
  pin_rc=$?
  set -e
  printf '%s\n' "$pin_out" >"$step/pin.txt"
  if [ "$pin_rc" -ne 0 ]; then
    echo "FAIL: pin_rc=$pin_rc" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi

  WID_HEX="$(awk -F= '/^WID_HEX=/{print $2}' "$PIN_FILE" | tail -n 1)"
  EMAIL="$(awk -F= '/^EMAIL=/{print $2}' "$PIN_FILE" | tail -n 1)"

  echo "WID_HEX=$WID_HEX" >"$step/meta.txt"
  echo "EMAIL=$EMAIL" >>"$step/meta.txt"

  if [ "$EMAIL" != "$EXPECTED_EMAIL" ]; then
    echo "FAIL: email_mismatch got=$EMAIL want=$EXPECTED_EMAIL" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi

  # 2) Validar que el WID existe (no BadWindow)
  if ! xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1; then
    echo "FAIL: badwindow $WID_HEX" | tee -a "$OUT/summary.txt"
    fail=1
    break
  fi

  # 3) Capture + URL sanity
  mkdir -p "$step/capture"
  set +e
  cap_out="$("$CAPTURE" "$WID_HEX" "$step/capture" 2>&1)"
  cap_rc=$?
  set -e
  printf '%s\n' "$cap_out" >"$step/capture/capture.txt"

  url_file="$step/capture/url.txt"
  url=""
  [ -r "$url_file" ] && url="$(cat "$url_file" | tr -d '\r')"
  echo "URL_CAPTURE=$url" >>"$step/meta.txt"

  # Si la URL no parece de ChatGPT, forzamos URL-lock a chatgpt.com y re-capturamos una vez
  if ! printf '%s' "$url" | grep -Eq '^https?://chatgpt\.com/'; then
    if [ -x "$ENSURE_URL" ]; then
      set +e
      ens_out="$("$ENSURE_URL" "$WID_HEX" "https://chatgpt.com/" 8 2>&1)"
      ens_rc=$?
      set -e
      printf '%s\n' "$ens_out" >"$step/ensure_url.txt"
      if [ "$ens_rc" -ne 0 ]; then
        echo "FAIL: ensure_url rc=$ens_rc" | tee -a "$OUT/summary.txt"
        fail=1
        break
      fi

      # re-capture
      mkdir -p "$step/capture2"
      set +e
      cap2_out="$("$CAPTURE" "$WID_HEX" "$step/capture2" 2>&1)"
      cap2_rc=$?
      set -e
      printf '%s\n' "$cap2_out" >"$step/capture2/capture.txt"
      url2=""
      [ -r "$step/capture2/url.txt" ] && url2="$(cat "$step/capture2/url.txt" | tr -d '\r')"
      echo "URL_CAPTURE2=$url2" >>"$step/meta.txt"

      if ! printf '%s' "$url2" | grep -Eq '^https?://chatgpt\.com/'; then
        echo "FAIL: url_not_chatgpt (after lock) <$url2>" | tee -a "$OUT/summary.txt"
        fail=1
        break
      fi
    else
      echo "FAIL: capture_not_chatgpt <$url> (and no ENSURE_URL helper)" | tee -a "$OUT/summary.txt"
      fail=1
      break
    fi
  fi

  # 4) Get URL via helper (si existe) para confirmar /c/ cuando aplique
  if [ -x "$GET_URL" ]; then
    set +e
    get_out="$(CHATGPT_WID_HEX="$WID_HEX" "$GET_URL" 2>&1 | head -n 5)"
    get_rc=$?
    set -e
    printf '%s\n' "$get_out" >"$step/get_url.txt"
    if [ "$get_rc" -ne 0 ]; then
      echo "FAIL: get_url rc=$get_rc" | tee -a "$OUT/summary.txt"
      fail=1
      break
    fi
    # Solo sanity: que esté en chatgpt.com
    if ! printf '%s' "$get_out" | grep -q 'https://chatgpt.com/'; then
      echo "FAIL: get_url_not_chatgpt" | tee -a "$OUT/summary.txt"
      fail=1
      break
    fi
  fi

  echo "OK: iter=$i wid=$WID_HEX email=$EMAIL" | tee -a "$OUT/summary.txt"
  sleep 0.15
done

if [ "$fail" -eq 0 ]; then
  echo "OK_STRESS_DIEGO_GATE iters=$ITER outdir=$OUT"
  exit 0
else
  echo "FAIL_STRESS_DIEGO_GATE outdir=$OUT" >&2
  exit 3
fi
