#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

say() {
  echo "== $* =="
}

say "A3 BASELINE"
./scripts/verify_a3_all.sh

PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"
if [[ -f "${PIN_FILE}" ]]; then
  export CHATGPT_WID_PIN_ONLY=1
  echo "PIN_FILE=${PIN_FILE}"
  pin_wid="$(head -n 1 "${PIN_FILE}" | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
  if [[ -n "${pin_wid:-}" ]]; then
    echo "PIN_WID=${pin_wid}"
    wins_pin="$(./scripts/x11_host_exec.sh 'wmctrl -l' 2>/dev/null || true)"
    title_pin="$(awk -v w="$pin_wid" '$1==w { $1=""; $2=""; $3=""; sub(/^ +/, ""); print; exit }' <<< "$wins_pin")"
    if [[ -n "${title_pin:-}" ]]; then
      echo "PIN_TITLE=${title_pin}"
    fi
  fi
fi

say "WID VERIFY"
./scripts/verify_chatgpt_get_wid.sh

say "WRAPPER SMOKE"
ask_err="$(mktemp)"
ask_out=""
set +e
ask_out="$(./scripts/lucy_chatgpt_ask.sh "Respondé exactamente con: OK" 2>"$ask_err")"
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  echo "ERROR: wrapper ask failed rc=$rc" >&2
  cat "$ask_err" >&2 || true
  exit 1
fi
printf '%s\n' "$ask_out"
if ! grep -q "ANSWER_LINE=.*: OK" <<<"$ask_out"; then
  echo "ERROR: wrapper output missing OK" >&2
  exit 1
fi
fore_dir="$(sed -n 's/^FORENSICS_DIR=//p' "$ask_err" | tail -n 1)"
echo "FORENSICS_DIR=${fore_dir}"

say "LOCK TEST"
rm -f /tmp/lucy_chatgpt_bridge.lock /tmp/lucy_chatgpt_bridge/lock 2>/dev/null || true

(
  LUCY_CHATGPT_LOCK_TIMEOUT_SEC=120 ./scripts/lucy_chatgpt_ask.sh "Respondé exactamente con: OK" \
    1> /tmp/ask1.out 2> /tmp/ask1.err
) &
p1=$!

sleep 1

(
  LUCY_CHATGPT_LOCK_TIMEOUT_SEC=5 ./scripts/lucy_chatgpt_ask.sh "Respondé exactamente con: OK" \
    1> /tmp/ask2.out 2> /tmp/ask2.err
) &
p2=$!

wait "$p1" || true
wait "$p2" || true

if ! grep -q "ANSWER_LINE=.*: OK" /tmp/ask1.out; then
  echo "ERROR: ask1 missing OK" >&2
  exit 1
fi
ask2_ok=0
if grep -q "ANSWER_LINE=.*: OK" /tmp/ask2.out; then
  ask2_ok=1
fi

if ! grep -q "LOCK_ACQUIRED=1" /tmp/ask1.err; then
  echo "ERROR: ask1 missing LOCK_ACQUIRED" >&2
  exit 1
fi
if ! grep -q "LOCK_RELEASED=1" /tmp/ask1.err; then
  echo "ERROR: ask1 missing LOCK_RELEASED" >&2
  exit 1
fi

if [[ "${ask2_ok}" -eq 1 ]]; then
  if ! grep -q "LOCK_ACQUIRED=1" /tmp/ask2.err; then
    echo "ERROR: ask2 missing LOCK_ACQUIRED" >&2
    exit 1
  fi
  if ! grep -q "LOCK_RELEASED=1" /tmp/ask2.err; then
    echo "ERROR: ask2 missing LOCK_RELEASED" >&2
    exit 1
  fi
else
  if ! grep -q "ERROR: LOCK_TIMEOUT" /tmp/ask2.err; then
    echo "ERROR: ask2 neither OK nor LOCK_TIMEOUT" >&2
    exit 1
  fi
fi

waited_max="$(awk -F'=' '/LOCK_ACQUIRED=1/{for(i=1;i<=NF;i++){if($i ~ /^waited_ms/){print $(i+1)}}}' /tmp/ask1.err /tmp/ask2.err | sort -n | tail -n 1)"
if [[ -z "${waited_max:-}" ]]; then
  waited_max=0
fi
if [[ "${ask2_ok}" -eq 0 ]] && grep -q "ERROR: LOCK_TIMEOUT" /tmp/ask2.err; then
  waited_max=$(( waited_max > 0 ? waited_max : 1 ))
fi
if [[ "$waited_max" -le 0 ]]; then
  echo "ERROR: lock did not wait (waited_ms=$waited_max)" >&2
  exit 1
fi

say "COPY ASSERT"
if [[ -z "${fore_dir:-}" ]]; then
  echo "ERROR: missing FORENSICS_DIR from wrapper" >&2
  exit 1
fi
if [[ ! -f "$fore_dir/copy.txt" ]]; then
  echo "ERROR: copy.txt not present" >&2
  exit 1
fi
if grep -q "Ningún archivo seleccionado" "$fore_dir/copy.txt"; then
  echo "ERROR: copy.txt contains UI noise" >&2
  exit 1
fi

rm -f "$ask_err" 2>/dev/null || true

echo "VERIFY_A4_ALL_OK"
