#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFIX_DIR="${ROOT_DIR}/runtime/openclaw"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-latest}"

mkdir -p "${PREFIX_DIR}"

echo "[install_openclaw] root=${ROOT_DIR}"
echo "[install_openclaw] prefix=${PREFIX_DIR}"
echo "[install_openclaw] version=${OPENCLAW_VERSION}"

npm install --prefix "${PREFIX_DIR}" "openclaw@${OPENCLAW_VERSION}" --no-fund --no-audit

echo "[install_openclaw] installed"
"${ROOT_DIR}/runtime/wrapper/openclaw.sh" --version
