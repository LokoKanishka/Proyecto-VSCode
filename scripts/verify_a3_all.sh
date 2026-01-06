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

# --- A3.12 timeouts (propagados desde verify_a3_all) ---
export A3_12_TIMEOUT="${A3_12_TIMEOUT:-260}"
export CHATGPT_ASK_TIMEOUT_SEC="${CHATGPT_ASK_TIMEOUT_SEC:-240}"
# --------------------------------------------------------

./scripts/verify_a3_12.sh

echo "VERIFY_A3_ALL_OK"
