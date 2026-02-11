#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[bootstrap] root: ${ROOT_DIR}"
echo "[bootstrap] instalando openclaw (moltbot upstream)"
"${ROOT_DIR}/runtime/install/install_openclaw.sh"
echo "[bootstrap] done"
