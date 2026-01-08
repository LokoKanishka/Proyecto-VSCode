#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT
export CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"

say() {
  echo "== $* =="
}

say "A3.12 FAST"
./scripts/verify_a3_12.sh

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

rm -f "$ask_err" 2>/dev/null || true

echo "VERIFY_A5_PAID_SMOKE_OK"
