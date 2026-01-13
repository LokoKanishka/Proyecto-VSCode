#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/chatgpt_copy_messages_strict.sh"

echo "== RUNNING STRICT COPY VERIFICATION (10 iterations) =="

failures=0
successes=0

for i in $(seq 1 10); do
  printf "Iter %2d: " "$i"
  # Clean clipboard first to ensure we are getting fresh data (optional but good)
  # But the script overwrites it anyway.
  
  out=$(mktemp)
  if "$SCRIPT" > "$out"; then
    bytes=$(wc -c < "$out")
    if [[ "$bytes" -gt 200 ]]; then
      echo "OK ($bytes bytes)"
      successes=$((successes+1))
    else
      echo "FAIL (too small: $bytes bytes)"
      failures=$((failures+1))
    fi
  else
    echo "FAIL (script exit code)"
    failures=$((failures+1))
  fi
  rm -f "$out"
  sleep 1
done

echo "== RESULTS =="
echo "Success: $successes"
echo "Failure: $failures"

if [[ "$failures" -eq 0 ]]; then
  exit 0
else
  exit 1
fi
