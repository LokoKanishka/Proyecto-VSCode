#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

say() {
  echo "== $* =="
}

rc=0

say "A4 ALL"
if ! ./scripts/verify_a4_all.sh; then
  echo "ERROR: verify_a4_all failed" >&2
  rc=1
fi

say "WEB SEARCH"
if ! ./scripts/verify_web_search_searxng.sh; then
  echo "ERROR: verify_web_search_searxng failed" >&2
  rc=1
fi

if [[ "$rc" -ne 0 ]]; then
  exit "$rc"
fi

echo "VERIFY_A5_ALL_OK"
