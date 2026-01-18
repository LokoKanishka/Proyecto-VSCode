#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# --- YouTube tolerant lock (avoid exact results URL mismatch) ---
YT_LOCK_PREFIX="${YT_LOCK_PREFIX:-https://www.youtube.com/}"
ENSURE_YT="${ROOT}/scripts/yt_ensure_url_in_window.sh"
ENSURE_YT_TOOL="${ROOT}/scripts/chrome_ensure_url_in_window.sh"
if [ -x "$ENSURE_YT" ]; then ENSURE_YT_TOOL="$ENSURE_YT"; fi

if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"
ENSURE="$ROOT/scripts/chrome_ensure_url_in_window.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"

SEND="$ROOT/scripts/chatgpt_ui_send_x11.sh"
COPY_CHAT="$ROOT/scripts/chatgpt_copy_chat_text.sh"

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"

Q_CHATGPT="¿Cuál es el nombre de pila de Borges?"
YT_QUERY="borges conferencia sobre la cegera"
YT_URL="https://www.youtube.com/results?search_query=borges+conferencia+sobre+la+cegera"

OUT="/tmp/lucy_once_cg_yt_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"
echo "OUTDIR=$OUT"

_need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING_DEP: $1" >&2; exit 2; }; }
_need wmctrl
_need xdotool

[ -x "$GUARD" ]  || { echo "ERROR_NO_GUARD: $GUARD" >&2; exit 2; }
[ -x "$ENSURE" ] || { echo "ERROR_NO_ENSURE: $ENSURE" >&2; exit 2; }
[ -x "$CAPTURE" ]|| { echo "ERROR_NO_CAPTURE: $CAPTURE" >&2; exit 2; }
[ -x "$SEND" ]   || { echo "ERROR_NO_SEND: $SEND" >&2; exit 2; }

echo "== STEP 1: GUARD DIEGO CLIENT (EMAIL) ==" | tee "$OUT/step.log"
set +e
guard_out="$(CHROME_PROFILE_NAME="$PROFILE_NAME" CHROME_DIEGO_EMAIL="$DIEGO_EMAIL" "$GUARD" "https://www.google.com/" 2>&1)"
guard_rc=$?
set -e
printf '%s\n' "$guard_out" >"$OUT/guard.txt"
if [ "$guard_rc" -ne 0 ]; then
  echo "FAIL_GUARD rc=$guard_rc (see $OUT/guard.txt)" >&2
  exit 3
fi

WID_HEX="$(printf '%s\n' "$guard_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
EMAIL="$(printf '%s\n' "$guard_out" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"
if [ -z "${WID_HEX:-}" ]; then
  echo "FAIL_NO_WID (see $OUT/guard.txt)" >&2
  exit 3
fi
if [ "${EMAIL:-}" != "$DIEGO_EMAIL" ]; then
  echo "FAIL_EMAIL_MISMATCH got=${EMAIL:-<empty>} expected=$DIEGO_EMAIL (see $OUT/guard.txt)" >&2
  exit 3
fi
echo "OK_GUARD WID_HEX=$WID_HEX EMAIL=$EMAIL" | tee -a "$OUT/step.log"

export CHROME_WID_HEX="$WID_HEX"
export CHATGPT_WID_HEX="$WID_HEX"
export CHATGPT_TARGET_URL="https://chatgpt.com/"
export CHATGPT_ALLOW_GUEST=1

echo "== STEP 2: CHATGPT URL-LOCK ==" | tee -a "$OUT/step.log"
set +e
ensure_cg="$("$ENSURE" "$WID_HEX" "https://chatgpt.com/" 12 2>&1)"
rc_cg=$?
set -e
printf '%s\n' "$ensure_cg" >"$OUT/ensure_chatgpt.txt"
if [ "$rc_cg" -ne 0 ]; then
  echo "FAIL_ENSURE_CHATGPT rc=$rc_cg (see $OUT/ensure_chatgpt.txt)" >&2
  exit 3
fi

mkdir -p "$OUT/capture_chatgpt_before"
"$CAPTURE" "$WID_HEX" "$OUT/capture_chatgpt_before" >/dev/null 2>&1 || true

echo "== STEP 3: SEND 1 QUESTION IN CHATGPT ==" | tee -a "$OUT/step.log"
printf '%s\n' "$Q_CHATGPT" >"$OUT/question.txt"

# Importante: mandamos SOLO este texto al input de ChatGPT (no al omnibox).
set +e
send_out="$("$SEND" "$Q_CHATGPT" 2>&1)"
send_rc=$?
set -e
printf '%s\n' "$send_out" >"$OUT/send_chatgpt.txt"
if [ "$send_rc" -ne 0 ]; then
  echo "FAIL_SEND_CHATGPT rc=$send_rc (see $OUT/send_chatgpt.txt)" >&2
  exit 3
fi

# Dale un toque para que aparezca la respuesta
sleep 6

mkdir -p "$OUT/capture_chatgpt_after"
"$CAPTURE" "$WID_HEX" "$OUT/capture_chatgpt_after" >/dev/null 2>&1 || true

if [ -x "$COPY_CHAT" ]; then
  set +e
  "$COPY_CHAT" >"$OUT/chat_text.txt" 2>&1
  set -e
fi

echo "OK_CHATGPT_SENT wid=$WID_HEX" | tee -a "$OUT/step.log"

echo "== STEP 4: YOUTUBE SEARCH (URL-LOCK BASE) ==" | tee -a "$OUT/step.log"
printf '%s\n' "$YT_QUERY" >"$OUT/youtube_query.txt"
printf '%s\n' "$YT_URL" >"$OUT/youtube_url.txt"

set +e
ensure_yt="$("$ENSURE_YT_TOOL" "$WID_HEX" "$YT_LOCK_PREFIX" 12 2>&1)"
rc_yt=$?
set -e
printf '%s\n' "$ensure_yt" >"$OUT/ensure_youtube.txt"
if [ "$rc_yt" -ne 0 ]; then
  echo "FAIL_ENSURE_YOUTUBE rc=$rc_yt (see $OUT/ensure_youtube.txt)" >&2
  exit 3
fi

mkdir -p "$OUT/capture_youtube"
"$CAPTURE" "$WID_HEX" "$OUT/capture_youtube" >/dev/null 2>&1 || true

echo "OK_YOUTUBE_SEARCH wid=$WID_HEX" | tee -a "$OUT/step.log"
echo "OK_ONCE_CG_YT outdir=$OUT wid=$WID_HEX email=$EMAIL"
