#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_LOG="/tmp/lucy_smoke_summary.log"
REPORT_DIR="$ROOT/reports"
SUMMARY="$REPORT_DIR/smoke_summary.md"
SKYSCANNER_SMOKE=${SKYSCANNER_SMOKE:-1}
BRIDGE_SMOKE=${BRIDGE_SMOKE:-0}
MEMORY_SMOKE=${MEMORY_SMOKE:-1}

mkdir -p "$REPORT_DIR"
> "$SMOKE_LOG"

echo "Starting smoke suite at $(date)" | tee -a "$SMOKE_LOG"

declare -A results

run_step() {
  local name="$1"
  local cmd="$2"
  echo "$name" | tee -a "$SMOKE_LOG"
  if eval "$cmd" >>"$SMOKE_LOG" 2>&1; then
    echo "   $name: ✅" | tee -a "$SMOKE_LOG"
    results["$name"]="✅"
  else
    echo "   $name: ❌" | tee -a "$SMOKE_LOG"
    results["$name"]="❌"
  fi
}

run_step "1) Health smoke" "./scripts/web_health_smoke.sh"
run_step "2) Plan verification" "./scripts/verify_skyscanner_plan.py"
if [ "$SKYSCANNER_SMOKE" -ne 0 ]; then
  run_step "3) Skyscanner smoke" "./scripts/skyscanner_smoke.sh"
else
  echo "3) Skyscanner smoke: skipped (SKYSCANNER_SMOKE=0)" | tee -a "$SMOKE_LOG"
  results["3) Skyscanner smoke"]="skipped"
fi
if [ "$BRIDGE_SMOKE" -ne 0 ]; then
  run_step "4) Bridge smoke" "./scripts/bridge_smoke.sh"
else
  echo "4) Bridge smoke: skipped (BRIDGE_SMOKE=0)" | tee -a "$SMOKE_LOG"
  results["4) Bridge smoke"]="skipped"
fi
if [ "$MEMORY_SMOKE" -ne 0 ]; then
  run_step "5) Memory snapshot smoke" "./scripts/memory_snapshot_smoke.py"
else
  echo "5) Memory snapshot smoke: skipped (MEMORY_SMOKE=0)" | tee -a "$SMOKE_LOG"
  results["5) Memory snapshot smoke"]="skipped"
fi

echo "Smoke suite finished at $(date)" | tee -a "$SMOKE_LOG"
echo "Summary log: $SMOKE_LOG"

{
  echo "# Smoke suite summary ($(date))"
  for key in "1) Health smoke" "2) Plan verification" "3) Skyscanner smoke" "4) Bridge smoke" "5) Memory snapshot smoke"; do
    echo "- **$key**: ${results[$key]}"
  done
  echo ""
  echo "Log: $SMOKE_LOG"
} > "$SUMMARY"

echo "Report generated at $SUMMARY"
