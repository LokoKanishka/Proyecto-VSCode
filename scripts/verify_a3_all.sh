#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Common env (sets X11_FILE_IPC_DIR, dispatcher timeout, etc.)
source "$ROOT/scripts/_verify_common.sh"

echo "== RUN A3 SUITE =="
./scripts/verify_a3_7.sh
./scripts/verify_a3_8.sh
./scripts/verify_a3_10.sh
./scripts/verify_a3_11.sh
./scripts/verify_a3_12.sh

echo "VERIFY_A3_ALL_OK"
