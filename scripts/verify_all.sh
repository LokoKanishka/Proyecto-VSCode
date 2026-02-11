#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${ROOT_DIR}/scripts/verify_smoke.sh"
"${ROOT_DIR}/scripts/verify_upstream.sh"
"${ROOT_DIR}/scripts/verify_models.sh"
"${ROOT_DIR}/scripts/verify_skills.sh"

echo "[verify_all] OK"
