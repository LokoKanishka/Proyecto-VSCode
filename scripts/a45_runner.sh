#!/usr/bin/env bash
set -euo pipefail

# filename: scripts/a45_runner.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

STAMP="$(date +%F_%H%M%S)"
LOGDIR="/tmp/lucy_a45_runner_$STAMP"
mkdir -p "$LOGDIR"

exec > >(tee -a "$LOGDIR/runner.log") 2>&1

TARGET_BRANCH="feat/a45-focus-hardening"
MAIN_BRANCH="main"
A8_RUNS=5
STRESS_ITERATIONS=10

log() {
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

record_static_info() {
  log "Recording repository status"
  git status -sb || true
  git log -3 --oneline || true
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    git rev-list --left-right --count origin/main...main || true
  else
    log "origin/main not found in refs, skipping rev-list"
  fi
  if command -v docker >/dev/null; then
    log "Docker status (SearxNG rows)"
    docker ps --format '{{.Names}}\t{{.Status}}' | grep -i searx || true
  else
    log "docker no disponible"
  fi
}

copy_verify_log() {
  local dest="$LOGDIR/last_verify.log"
  local latest
  if latest="$(ls -1t /tmp/verify_a8_day_start*.log 2>/dev/null | head -n1)"; then
    cp -f "$latest" "$dest"
    log "Copied last verify log to $dest"
  fi
}

copymeta_from_tmpdir() {
  local src="$1"
  local dest_root="$LOGDIR/lucy_ask_tmpdir"
  if [[ -d "$src" ]]; then
    mkdir -p "$dest_root"
    log "Gathering Lucy ask tmpdir content from $src"
    for f in focus_attempts.txt probe_copy.txt meta.txt copy.txt screenshot.png; do
      if [[ -e "$src/$f" ]]; then
        cp -f "$src/$f" "$dest_root/"
      fi
    done
    ls -la "$src" > "$dest_root/ls.txt" 2>/dev/null || true
  fi
}

gather_lucy_tmpdir_from_log() {
  local log_path="$1"
  if [[ -z "$log_path" || ! -f "$log_path" ]]; then
    return
  fi
  local match
  match="$(grep -o 'LUCY_ASK_TMPDIR=[^[:space:]]*' "$log_path" 2>/dev/null | head -n1 || true)"
  if [[ -n "$match" ]]; then
    local tmpdir="${match#*=}"
    copymeta_from_tmpdir "$tmpdir"
  fi
}

record_failure() {
  local stage="$1"
  local log_file="${2:-}"
  echo "FAIL_STAGE=$stage" > "$LOGDIR/fail.txt"
  echo "TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOGDIR/fail.txt"
  if [[ -n "$log_file" && -f "$log_file" ]]; then
    cp -f "$log_file" "$LOGDIR/last_run.log"
  fi
  copy_verify_log
  gather_lucy_tmpdir_from_log "$log_file"
  if [[ -d "$LOGDIR/lucy_ask_tmpdir" ]]; then
    log "Copied Lucy ask tmpdir data to $LOGDIR/lucy_ask_tmpdir"
  fi
  log "Recording failure for stage $stage"
  exit 1
}

run_searx_health() {
  local deadline=$(( $(date +%s) + 90 ))
  log "Waiting up to 90s for SearxNG health"
  while true; do
    if curl -fsS --max-time 2 http://127.0.0.1:8080/ >/dev/null; then
      log "SearxNG health check succeeded"
      return
    fi
    if (( $(date +%s) >= deadline )); then
      log "SEARX_NOT_READY after 90s, recording failure"
      record_failure "SEARX_NOT_READY"
    fi
    sleep 2
  done
}

run_a8_runs() {
  for (( i=1; i<=A8_RUNS; i++ )); do
    local log_a8="$LOGDIR/a8.$i.log"
    log "----- RUN A8 $i/$A8_RUNS -----"
    if ! ./scripts/verify_a8_day_start.sh 2>&1 | tee "$log_a8"; then
      log "verify_a8_day_start.sh failed on run $i"
      record_failure "A8_FAIL_RUN_$i" "$log_a8"
    fi
  done
}

copy_stress_summary() {
  local summary
  if summary="$(ls -1t /tmp/verify_a8_day_start*.stress*.summary*.tsv 2>/dev/null | head -n1)"; then
    cp -f "$summary" "$LOGDIR/stress.summary.tsv"
    log "Copied stress summary to $LOGDIR/stress.summary.tsv"
  fi
}

run_stress() {
  log "Running stress harness with ${STRESS_ITERATIONS} iterations"
  export A8_STRESS_N="$STRESS_ITERATIONS"
  if ! ./scripts/verify_a8_day_start_stress.sh 2>&1 | tee "$LOGDIR/stress.log"; then
    log "Stress harness exited with failure"
    record_failure "STRESS_FAIL"
  fi
  copy_stress_summary
  if grep -q 'ok=10' "$LOGDIR/stress.log" 2>/dev/null; then
    log "Stress log reports ok=10"
  elif [[ -f "$LOGDIR/stress.summary.tsv" ]] && grep -q 'ok=10' "$LOGDIR/stress.summary.tsv" 2>/dev/null; then
    log "Stress summary reports ok=10"
  else
    log "Stress run did not report %ok=10%"
    record_failure "STRESS_NO_OK"
  fi
}

merge_and_push() {
  log "Preparing commit/merge + push"
  git add -A
  if git diff --cached --quiet; then
    log "No staged changes detected, skipping commit"
  else
    git commit -m "A45: harden input focus + prevent extended-thinking loop"
  fi
  git checkout "$MAIN_BRANCH"
  git merge --ff-only "$TARGET_BRANCH"
  if ! ./scripts/net_check.sh; then
    log "net_check.sh failed, leaving commit local"
    record_failure "FAIL_NET"
  fi
  git push origin "$MAIN_BRANCH"
  touch "$LOGDIR/success.txt"
  log "A45_GREEN"
}

main() {
  log "A45 runner starting"
  record_static_info
  if [[ "$(git branch --show-current)" != "$TARGET_BRANCH" ]]; then
    log "Unexpected branch, expected $TARGET_BRANCH"
    record_failure "BRANCH_MISMATCH"
  fi
  run_searx_health
  run_a8_runs
  run_stress
  merge_and_push
}

main "$@"
