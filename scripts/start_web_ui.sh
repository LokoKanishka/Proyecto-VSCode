#!/usr/bin/env bash
set -e

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv-lucy-voz"

# Ir al proyecto
cd "$PROJECT_DIR"

# Verificar entorno
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Entorno virtual no encontrado."
    echo "   Ejecutá: python3 -m venv .venv-lucy-voz && source .venv-lucy-voz/bin/activate && pip install -r lucy_voice/requirements.txt"
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo "========================================="
echo "   🌐 Lucy Voice Web UI"
echo "========================================="
echo ""
echo "  Iniciando servidor en:"
echo "  http://localhost:5000"
echo ""
echo "  Presioná Ctrl+C para detener"
echo ""
echo "========================================="

# Ejecutar servidor Flask
python lucy_web/app.py
