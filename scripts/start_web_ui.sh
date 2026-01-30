#!/usr/bin/env bash
set -euo pipefail

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

# Verificar dependencias críticas de audio
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "⚠️  ffmpeg no encontrado. Instalá con: sudo apt-get install ffmpeg"
fi
if ! python3 -c "import soundfile" >/dev/null 2>&1; then
    echo "⚠️  soundfile no instalado en el venv. Ejecutá: pip install soundfile"
fi

DEFAULT_PORT="${LUCY_WEB_PORT:-5000}"
port="$DEFAULT_PORT"
while ss -ltn "( sport = :$port )" >/dev/null 2>&1; do
    ((port++))
done

LUCY_WEB_PORT="$port"
export LUCY_WEB_PORT

HOST="${LUCY_WEB_HOST:-0.0.0.0}"
LUCY_WEB_HOST="$HOST"
export LUCY_WEB_HOST

echo "========================================="
echo "   🌐 Lucy Voice Web UI"
echo "========================================="
echo ""
echo "  Iniciando servidor en:"
echo "  http://$HOST:$port"
echo ""
echo "  Presioná Ctrl+C para detener"
echo ""
echo "========================================="

# Ejecutar servidor Flask (modo dev seguro por variable)
export LUCY_WEB_ALLOW_UNSAFE="${LUCY_WEB_ALLOW_UNSAFE:-1}"
.venv-lucy-voz/bin/python lucy_web/app.py
