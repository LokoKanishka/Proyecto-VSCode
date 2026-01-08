#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="${VERIFY_A6_STAMP:-$(date +%s)}"
LOG_PATH="${VERIFY_A6_LOG:-/tmp/verify_a6_all.a36.${STAMP}.log}"
A5_LOG="${VERIFY_A5_LOG:-/tmp/verify_a5_all.paid.a36.${STAMP}.log}"
: > "$LOG_PATH"
: > "$A5_LOG"
exec > >(tee "$LOG_PATH") 2>&1

say() {
  echo "== $* =="
}

say "DUMMY PIPE"
CHATGPT_TARGET=dummy ./scripts/verify_ui_dummy_pipe.sh

say "WEB SEARCH"
./scripts/verify_web_search_searxng.sh

say "A5 PAID RUN 1"
CHATGPT_TARGET=paid ./scripts/verify_a5_all.sh | tee "$A5_LOG"

say "A5 PAID RUN 2"
CHATGPT_TARGET=paid ./scripts/verify_a5_all.sh | tee -a "$A5_LOG"

echo "VERIFY_A6_ALL_OK"
