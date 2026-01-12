#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv-lucy-voz/bin/python3"

echo "== py_compile =="
"$PY" -m py_compile \
  lucy_agents/voice_actions.py \
  lucy_tools/audit_trazabilidad.py \
  lucy_agents/voice_modular_node.py \
  external/nodo-de-voz-modular-de-lucy/tts.py

echo
echo "== audit_trazabilidad =="
./scripts/audit_trazabilidad.sh
grep -n "Hallazgos:" -n docs/AUDIT_TRAZABILIDAD.md || true

# limpieza de outputs locales (aunque estén ignorados)
rm -f reports/audit_trazabilidad.json || true

echo
echo "== submodules =="
git submodule status --recursive

echo
echo "== git status =="
git status --porcelain

