#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

A8_STRESS_N="${A8_STRESS_N:-10}"
A8_STRESS_SLEEP="${A8_STRESS_SLEEP:-1}"
A8_STRESS_STOP_ON_FAIL="${A8_STRESS_STOP_ON_FAIL:-1}"
A8_STRESS_TARGET="${A8_STRESS_TARGET:-paid}"

SUMMARY="/tmp/verify_a8_day_start.a45.stress.summary.tsv"
printf "i\tok\tseconds\tpaid_wid\tthread_url\tservices_mode\tlog_path\n" > "$SUMMARY"

ok_count=0
total=0
sum_s=0
max_s=0
thread_ref=""

for i in $(seq 1 "$A8_STRESS_N"); do
  stamp="$(date +%Y%m%d_%H%M%S)_$RANDOM"
  log="/tmp/verify_a8_day_start.a45.stress.${i}.${stamp}.log"
  summary="/tmp/verify_a8_day_start.${stamp}.summary.txt"
  start_s="$(date +%s)"

  set +e
  CHATGPT_TARGET="$A8_STRESS_TARGET" VERIFY_A8_STAMP="$stamp" ./scripts/verify_a8_day_start.sh 2>&1 | tee "$log"
  rc=$?
  set -e

  end_s="$(date +%s)"
  dur_s=$(( end_s - start_s ))
  if [[ "$dur_s" -lt 0 ]]; then dur_s=0; fi

  services_mode="$(grep -m1 'SERVICES_MODE=' "$log" 2>/dev/null | sed 's/.*SERVICES_MODE=//' | awk '{print $1}')"
  thread_url=""
  paid_wid=""
  if [[ -f "$summary" ]]; then
    thread_url="$(awk -F= '/^thread_file_url=/{print $2}' "$summary" | tail -n 1)"
    paid_wid="$(awk -F= '/^paid_wid=/{print $2}' "$summary" | tail -n 1)"
  fi

  ok=1
  thread_changed=0
  if [[ "$rc" -ne 0 ]]; then ok=0; fi
  if [[ -z "$thread_url" ]]; then ok=0; fi
  if [[ -z "$paid_wid" ]]; then ok=0; fi
  if [[ -n "${services_mode:-}" && "${services_mode}" == "failed" ]]; then ok=0; fi
  if [[ -n "$thread_ref" && -n "$thread_url" && "$thread_url" != "$thread_ref" ]]; then
    ok=0
    thread_changed=1
  fi
  if [[ -z "$thread_ref" && -n "$thread_url" ]]; then
    thread_ref="$thread_url"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$i" "$ok" "$dur_s" "$paid_wid" "$thread_url" "${services_mode:-}" "$log" >> "$SUMMARY"

  total="$i"
  sum_s=$((sum_s + dur_s))
  if [[ "$dur_s" -gt "$max_s" ]]; then max_s="$dur_s"; fi

  if [[ "$ok" -eq 1 ]]; then
    ok_count=$((ok_count + 1))
  else
    printf 'A8_STRESS_FAIL i=%s log=%s rc=%s thread_changed=%s\n' "$i" "$log" "$rc" "$thread_changed" >&2
    if [[ "$A8_STRESS_STOP_ON_FAIL" -eq 1 ]]; then
      break
    fi
  fi

  sleep "$A8_STRESS_SLEEP"
done

avg_s=0
if [[ "$total" -gt 0 ]]; then
  avg_s=$((sum_s / total))
fi

echo "A8_STRESS_RESULT ok_count=${ok_count} total=${total} avg_s=${avg_s} max_s=${max_s} summary=${SUMMARY}"
if [[ "$ok_count" -ne "$total" ]]; then
  exit 1
fi
