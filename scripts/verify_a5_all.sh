#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

say() {
  echo "== $* =="
}

say "A4 ALL"
./scripts/verify_a4_all.sh

say "WEB SEARCH"
./scripts/verify_web_search_searxng.sh

echo "VERIFY_A5_ALL_OK"
