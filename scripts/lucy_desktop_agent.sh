#!/usr/bin/env bash
# Lanzador del Lucy Desktop Agent (manos locales)
set -euo pipefail

# Ir a la raíz del proyecto (carpeta padre de scripts/)
cd "$(dirname "$0")/.." || {
  echo "[LucyDesktop] No pude encontrar la raíz del proyecto." >&2
  exit 1
}

# Activar entorno virtual de Lucy voz, si existe
if [[ -d ".venv-lucy-voz" ]]; then
  # shellcheck disable=SC1091
  source ".venv-lucy-voz/bin/activate"
else
  echo "[LucyDesktop] Aviso: no encontré .venv-lucy-voz, usando Python del sistema." >&2
fi

# Ejecutar el agente de escritorio (modo interactivo por defecto)
python lucy_agents/desktop_agent.py "$@"
