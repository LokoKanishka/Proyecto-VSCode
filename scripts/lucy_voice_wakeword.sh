# LEGACY: script de Lucy voz original (wakeword/PTT). No se usa por defecto.

#!/usr/bin/env bash
# set -euo pipefail

# === Config básica ===
# Calcular la raíz del proyecto de forma portable (carpeta padre de scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv-lucy-voz"

echo "[LucyVoice] Iniciando Lucy voz (modo wake word simple)..."

# 1) Ir al proyecto
cd "$PROJECT_DIR"

# 2) Verificar que exista el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
  echo "[LucyVoice][ERROR] No se encontró el entorno virtual en:"
  echo "  $VENV_DIR"
  echo "Crealo de nuevo con algo como:"
  echo "  cd \"$PROJECT_DIR\""
  echo "  python3 -m venv .venv-lucy-voz"
  echo "  source .venv-lucy-voz/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

# 3) Activar entorno virtual
source "$VENV_DIR/bin/activate"

# 4) Lanzar Lucy voz (wakeword + pipeline de voz)
python -m lucy_voice.wakeword.listener
