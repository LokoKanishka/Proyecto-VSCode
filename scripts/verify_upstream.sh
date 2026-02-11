#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${ROOT_DIR}/runtime/wrapper/openclaw.sh"

if [[ ! -x "${WRAPPER}" ]]; then
  echo "[verify_upstream] missing wrapper: ${WRAPPER}" >&2
  exit 1
fi

echo "[verify_upstream] check --version"
"${WRAPPER}" --version

echo "[verify_upstream] check help command"
"${WRAPPER}" --help >/dev/null

echo "[verify_upstream] upstream smoke OK"
