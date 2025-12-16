#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

mkdir -p reports docs

python3 scripts/audit_trazabilidad.py \
  --roots scripts lucy_agents external/nodo-de-voz-modular-de-lucy \
  --out-md docs/AUDIT_TRAZABILIDAD.md \
  --out-json reports/audit_trazabilidad.json

if command -v code >/dev/null 2>&1; then
  code docs/AUDIT_TRAZABILIDAD.md
fi

echo "Listo: docs/AUDIT_TRAZABILIDAD.md"

