#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="/tmp/lucy_verify_chrome_routing_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"

OPEN_YT="$ROOT/scripts/youtube_open_diego.sh"
OPEN_CHATGPT="$ROOT/scripts/chatgpt_chrome_open.sh"
RESOLVE_YT="$ROOT/scripts/yt_resolve_wid_by_url.sh"
RESOLVE_CHATGPT="$ROOT/scripts/chatgpt_resolve_wid_by_url.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"
ENSURE_READY="$ROOT/scripts/chatgpt_ensure_ready.sh"
YT_PIN="$OUT/yt_wid.pin"
CG_PIN="$OUT/chatgpt_wid.pin"

echo "OUTDIR=$OUT"

focus_tab() {
  local wid_hex="$1"
  local tab="$2"
  local wid_dec
  wid_dec=$((wid_hex))
  wmctrl -ia "$wid_hex" 2>/dev/null || true
  xdotool windowactivate --sync "$wid_dec" 2>/dev/null || true
  sleep 0.15
  if [[ "$tab" =~ ^[1-9]$ ]]; then
    xdotool key --window "$wid_dec" --clearmodifiers "ctrl+$tab" 2>/dev/null || true
    sleep 0.15
  fi
}

echo "[VERIFY] Open YouTube (Diego profile)..." >&2
"$OPEN_YT" "https://www.youtube.com/" >/dev/null 2>&1 || true
sleep 3

echo "[VERIFY] Resolve YouTube WID by URL..." >&2
set +e
YOUTUBE_WID_PIN_FILE="$YT_PIN" yt_out="$("$RESOLVE_YT" 12 9 2>&1)"
yt_rc=$?
set -e
printf '%s\n' "$yt_out" >"$OUT/resolve_youtube.txt"
if [ "$yt_rc" -ne 0 ]; then
  echo "ERROR_RESOLVE_YOUTUBE rc=$yt_rc" >&2
  exit 3
fi
yt_wid="$(printf '%s\n' "$yt_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
yt_tab="$(printf '%s\n' "$yt_out" | awk -F= '/^TAB=/{print $2}' | tail -n 1)"
if [ -z "${yt_wid:-}" ]; then
  echo "ERROR_RESOLVE_YOUTUBE: missing WID_HEX" >&2
  exit 3
fi
mkdir -p "$OUT/youtube"
focus_tab "$yt_wid" "$yt_tab"
"$CAPTURE" "$yt_wid" "$OUT/youtube" >"$OUT/youtube/capture.txt" 2>&1 || true

echo "[VERIFY] Open ChatGPT (Diego profile)..." >&2
"$OPEN_CHATGPT" >/dev/null 2>&1 || true
sleep 3

echo "[VERIFY] Resolve ChatGPT WID by URL..." >&2
set +e
CHATGPT_WID_PIN_FILE="$CG_PIN" cg_out="$("$RESOLVE_CHATGPT" 12 9 2>&1)"
cg_rc=$?
set -e
printf '%s\n' "$cg_out" >"$OUT/resolve_chatgpt.txt"
if [ "$cg_rc" -ne 0 ]; then
  echo "ERROR_RESOLVE_CHATGPT rc=$cg_rc" >&2
  exit 3
fi
cg_wid="$(printf '%s\n' "$cg_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
cg_tab="$(printf '%s\n' "$cg_out" | awk -F= '/^TAB=/{print $2}' | tail -n 1)"
cg_url="$(printf '%s\n' "$cg_out" | awk -F= '/^URL=/{print $2}' | tail -n 1 | sed 's/^<<<//;s/>>>$//')"
if [ -z "${cg_wid:-}" ]; then
  echo "ERROR_RESOLVE_CHATGPT: missing WID_HEX" >&2
  exit 3
fi
mkdir -p "$OUT/chatgpt"
focus_tab "$cg_wid" "$cg_tab"
"$CAPTURE" "$cg_wid" "$OUT/chatgpt" >"$OUT/chatgpt/capture.txt" 2>&1 || true

echo "[VERIFY] Ensure ChatGPT ready..." >&2
set +e
CHATGPT_ALLOW_GUEST=1 CHATGPT_STRICT_COPY_MIN_BYTES=40 CHATGPT_WID_HEX="$cg_wid" \
  CHATGPT_TARGET_URL="$cg_url" "$ENSURE_READY" >"$OUT/ensure_ready.txt" 2>&1
ready_rc=$?
set -e
if [ "$ready_rc" -ne 0 ]; then
  echo "ERROR_CHATGPT_READY rc=$ready_rc (see $OUT/ensure_ready.txt)" >&2
  exit 3
fi

echo "OK_VERIFY_DESKTOP_CHROME_ROUTING outdir=$OUT"
