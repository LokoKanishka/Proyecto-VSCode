#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI="${ROOT_DIR}/runtime/openclaw/node_modules/.bin/openclaw"

if [[ ! -x "${CLI}" ]]; then
  echo "[openclaw-wrapper] missing CLI: ${CLI}" >&2
  echo "[openclaw-wrapper] run: ./runtime/install/install_openclaw.sh" >&2
  exit 1
fi

exec "${CLI}" "$@"
