#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_LOG="/tmp/lucy_smoke_summary.log"
REPORT_DIR="$ROOT/reports"
SUMMARY="$REPORT_DIR/smoke_summary.md"

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
run_step "3) Skyscanner smoke" "./scripts/skyscanner_smoke.sh"

echo "Smoke suite finished at $(date)" | tee -a "$SMOKE_LOG"
echo "Summary log: $SMOKE_LOG"

{
  echo "# Smoke suite summary ($(date))"
  for key in "1) Health smoke" "2) Plan verification" "3) Skyscanner smoke"; do
    echo "- **$key**: ${results[$key]}"
  done
  echo ""
  echo "Log: $SMOKE_LOG"
} > "$SUMMARY"

echo "Report generated at $SUMMARY"
