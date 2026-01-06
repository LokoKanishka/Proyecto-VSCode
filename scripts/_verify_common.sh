#!/usr/bin/env bash
set -euo pipefail
cd "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

export X11_FILE_IPC_DIR="${X11_FILE_IPC_DIR:-$PWD/diagnostics/x11_file_ipc}"
export LUCY_DISPATCHER_TIMEOUT="${LUCY_DISPATCHER_TIMEOUT:-25}"
unset LUCY_DISPATCHER_FAKE || true

need_file() {
  local p="$1"
  if [[ -z "${p:-}" || ! -f "$p" ]]; then
    echo "VERIFY_FAIL: file missing: $p" >&2
    exit 2
  fi
}
