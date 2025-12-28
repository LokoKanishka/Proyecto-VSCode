#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

N="${1:-5}"

ASK_TIMEOUT_SEC="${ASK_TIMEOUT_SEC:-45}"
WATCHDOG_SEC="${WATCHDOG_SEC:-55}"
RETRY_TIMEOUT_SEC="${RETRY_TIMEOUT_SEC:-30}"

export X11_FILE_IPC_DIR="${X11_FILE_IPC_DIR:-$ROOT/diagnostics/x11_file_ipc}"
source "$ROOT/scripts/x11_env.sh" || true
export CHATGPT_BRIDGE_PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"

panic() {
  if [[ -x /tmp/lucy_panic.sh ]]; then
    /tmp/lucy_panic.sh >/dev/null 2>&1 || true
  else
    pkill -f 'chatgpt_ui_ask_x11.sh' 2>/dev/null || true
    pkill -f 'chatgpt_copy_chat_text.sh' 2>/dev/null || true
    pkill -f '/scripts/x11_wrap/xdotool' 2>/dev/null || true
    pkill -x xdotool 2>/dev/null || true
  fi
}

sanitize_file() {
  tr -d '\r' <"$1" | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
}

copy_chat_sanitized() {
  local out="/tmp/lcp_live_chat_now.txt"
  : >"$out"
  : >/tmp/lcp_live_copy.err
  set +e
  CHATGPT_WID_HEX="$CHATGPT_WID_HEX" timeout 12s "$ROOT/scripts/chatgpt_copy_chat_text.sh" >"$out" 2>/tmp/lcp_live_copy.err
  set -e
  sanitize_file "$out"
}

ts="$(date +%s)"
LOG="/tmp/lcp_live_metrics_${ts}.tsv"
echo -e "i\trc\tms\tok\treason\tans" > "$LOG"

echo "PATCHED=scripts/smoke/lcp_live_metrics.sh"
echo
echo "LOG=$LOG"
echo "N=$N ASK_TIMEOUT_SEC=$ASK_TIMEOUT_SEC WATCHDOG_SEC=$WATCHDOG_SEC RETRY_TIMEOUT_SEC=$RETRY_TIMEOUT_SEC"
echo

# ping file-agent (si esta caido, abortamos temprano)
PING_OUT="$(timeout 6s "$ROOT/scripts/x11_file_call.sh" "echo LCP_PING_$ts" || true)"
if ! printf '%s\n' "$PING_OUT" | head -n 1 | grep -qx 'RC=0'; then
  echo "ERROR: file-agent no responde"
  printf '%s\n' "$PING_OUT" | sed -n '1,12p'
  exit 10
fi

# ensure bridge + wid
timeout 10s "$ROOT/scripts/chatgpt_bridge_ensure.sh" >/dev/null 2>&1 || true
WID="$("$ROOT/scripts/chatgpt_get_wid.sh" 2>/dev/null || true)"
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX"
  exit 11
fi
export CHATGPT_WID_HEX="$WID"
echo "CHATGPT_WID_HEX=$CHATGPT_WID_HEX"
echo

# warmup
echo "WARMUP (timeout 25s)..."
: >/tmp/lcp_live_warm.err
t0="$(date +%s%3N)"
set +e
WARM_ANS="$(timeout 25s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" 2>/tmp/lcp_live_warm.err)"
WARM_RC=$?
set -e
t1="$(date +%s%3N)"
echo "WARMUP rc=$WARM_RC ms=$((t1-t0))"
echo

okc=0
failc=0
ms_list=()

for i in $(seq 1 "$N"); do
  iter_err="/tmp/lcp_live_iter_${ts}_${i}.err"
  : >"$iter_err"

  t0="$(date +%s%3N)"
  ( sleep "$WATCHDOG_SEC"; panic ) & wd=$!

  set +e
  ANS="$(timeout "${ASK_TIMEOUT_SEC}s" "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" 2>"$iter_err")"
  RC=$?
  set -e

  kill "$wd" >/dev/null 2>&1 || true
  t1="$(date +%s%3N)"
  ms=$((t1-t0))

  ok=0
  reason="fail"

  if [[ "$RC" -eq 0 ]] && printf '%s\n' "$ANS" | grep -Eq '^LUCY_ANSWER_[0-9_]+: OK$'; then
    ok=1
    reason="ok"
  fi

  # timeout: autopsia (late) + retry 1 vez
  if [[ "$ok" -eq 0 && "$RC" -eq 124 ]]; then
    tok="$(grep -oE 'LUCY_ANSWER_[0-9_]+' "$iter_err" | tail -n 1 || true)"
    if [[ -n "${tok:-}" ]]; then
      chat_clean="$(copy_chat_sanitized || true)"
      if printf '%s\n' "$chat_clean" | grep -Fq "^${tok}: OK"; then
        ok=1
        reason="late"
        RC=0
        ANS="${tok}: OK"
      fi
    fi

    if [[ "$ok" -eq 0 ]]; then
      iter_err2="/tmp/lcp_live_iter_${ts}_${i}_retry.err"
      : >"$iter_err2"

      t0b="$(date +%s%3N)"
      ( sleep "$WATCHDOG_SEC"; panic ) & wd2=$!

      set +e
      ANS2="$(timeout "${RETRY_TIMEOUT_SEC}s" "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" 2>"$iter_err2")"
      RC2=$?
      set -e

      kill "$wd2" >/dev/null 2>&1 || true
      t1b="$(date +%s%3N)"
      ms=$((t1b-t0)) # total hasta el final del retry

      if [[ "$RC2" -eq 0 ]] && printf '%s\n' "$ANS2" | grep -Eq '^LUCY_ANSWER_[0-9_]+: OK$'; then
        ok=1
        reason="retry"
        RC=0
        ANS="$ANS2"
      else
        RC="$RC2"
        ANS="$ANS2"
      fi
    fi
  fi

  if [[ "$ok" -eq 1 ]]; then okc=$((okc+1)); else failc=$((failc+1)); fi
  ms_list+=("$ms")

  ans1="$(printf '%s\n' "$ANS" | head -n 1 | tr -d '\r' | sed 's/\t/ /g' | cut -c1-120)"
  printf "%02d/%02d rc=%s ms=%s ok=%s (%s)\n" "$i" "$N" "$RC" "$ms" "$ok" "$reason"
  echo -e "${i}\t${RC}\t${ms}\t${ok}\t${reason}\t${ans1}" >>"$LOG"
done

ms_sorted="$(printf '%s\n' "${ms_list[@]}" | sort -n)"
ms_min="$(printf '%s\n' "$ms_sorted" | head -n 1)"
ms_max="$(printf '%s\n' "$ms_sorted" | tail -n 1)"
ms_avg="$(printf '%s\n' "${ms_list[@]}" | awk '{s+=$1} END{printf "%.0f\n", s/NR}')"
ms_p50="$(printf '%s\n' "$ms_sorted" | awk '{a[NR]=$1} END{n=NR; idx=int((n+1)/2); print a[idx]}')"

echo
echo "OK=$okc FAIL=$failc"
echo "ms_min=$ms_min ms_p50=$ms_p50 ms_avg=$ms_avg ms_max=$ms_max"
echo
echo "ASK_ERR_TAIL (ultimo iter):"
tail -n 30 "$iter_err" 2>/dev/null || true
echo "WARM_ERR_TAIL:"
tail -n 30 /tmp/lcp_live_warm.err 2>/dev/null || true
