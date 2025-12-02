#!/usr/bin/env bash
set -euo pipefail

echo "=== Limpieza del sistema de voz viejo (wakeword/Pipecat) ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKUP_ROOT="${PROJECT_ROOT}/legacy"
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
BACKUP_DIR="${BACKUP_ROOT}/old_voice_system-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

move_if_exists() {
  local path="$1"
  if [ -e "${PROJECT_ROOT}/${path}" ]; then
    echo "→ Moviendo ${path} → ${BACKUP_DIR}/"
    mv "${PROJECT_ROOT}/${path}" "${BACKUP_DIR}/"
  else
    echo "→ No existe ${path}, nada que mover."
  fi
}

echo
echo "[1/3] Moviendo paquete de Python del pipeline viejo (lucy_voice/)…"
move_if_exists "lucy_voice"

echo
echo "[2/3] Moviendo scripts de voz viejos (wakeword / PTT / pruebas mic)…"
move_if_exists "scripts/lucy_voice_wakeword.sh"
move_if_exists "scripts/lucy_voice_ptt.sh"
move_if_exists "scripts/lucy_voice_mic_roundtrip.sh"
move_if_exists "scripts/lucy_voice_chat.sh"

echo
echo "[3/3] Moviendo scripts de fix del pipeline viejo…"
move_if_exists "fix_lucy_voice_all.sh"
move_if_exists "fix_pipeline_only.sh"
move_if_exists "fix_pipeline_output_clean.sh"
move_if_exists "fix_pipeline_recording_simple.sh"
move_if_exists "fix_wakeword_dynamic.sh"
move_if_exists "fix_wakeword_only.sh"
move_if_exists "fix_wakeword_simple_voice.sh"

echo
echo "✅ Listo. Todo lo viejo se movió a:"
echo "   ${BACKUP_DIR}"
echo
echo "Recordá:"
echo "  - El nodo modular sigue en external/"
echo "  - El lanzador oficial es scripts/lucy_voice_modular_node.sh"
echo
echo "Podés revisar con:  git status"
