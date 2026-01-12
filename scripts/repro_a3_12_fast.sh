#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ASK="$ROOT/scripts/chatgpt_ui_ask_x11.sh"
ENSURE_THREAD="$ROOT/scripts/chatgpt_paid_ensure_test_thread.sh"

N="${1:-10}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARTIFACTS_DIR="/tmp/repro_a3_12_fast_artifacts_${TIMESTAMP}"
mkdir -p "$ARTIFACTS_DIR"

echo "== REPRO A3.12 FAST (N=$N) =="
echo "Artifacts: $ARTIFACTS_DIR"
echo "RC | REQ | ANS | BYTES | LOG"
echo "---|-----|-----|-------|----"

for i in $(seq 1 "$N"); do
    LOG_FILE="/tmp/repro_a3_12_fast.$i.$TIMESTAMP.log"
    
    # Ensure test thread
    "$ENSURE_THREAD" >/dev/null 2>&1 || true
    
    # Run ask
    RC=0
    TOKEN="REPRO_${i}_${TIMESTAMP}"
    LUCY_ASK_TMPDIR="$ARTIFACTS_DIR/run_$i" \
    "$ASK" "Repro run $i - Token $TOKEN" >"$LOG_FILE" 2>&1 || RC=$?
    
    # Analyze
    HAS_REQ=0
    grep -q "LUCY_REQ_" "$LOG_FILE" && HAS_REQ=1 || true
    
    HAS_ANS=0
    grep -q "LUCY_ANSWER_" "$LOG_FILE" && HAS_ANS=1 || true
    
    BYTES=0
    if [[ -f "$ARTIFACTS_DIR/run_$i/copy.txt" ]]; then
        BYTES=$(wc -c < "$ARTIFACTS_DIR/run_$i/copy.txt")
    fi
    
    printf "%2d | %3s | %3s | %5d | %s\n" "$RC" "$HAS_REQ" "$HAS_ANS" "$BYTES" "$(basename "$LOG_FILE")"
done
