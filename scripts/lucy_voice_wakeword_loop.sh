#!/usr/bin/env bash
# Script para arrancar Lucy Voice en modo "Wake Word Loop"
# Escucha "Hey Jarvis" -> Activa Lucy -> Graba -> Responde -> Vuelve a escuchar

set -e

# Asegurar que estamos en el directorio correcto (asumiendo estructura estándar)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== Iniciando Lucy Voice Wake Word Loop ==="
echo "Directorio de trabajo: $(pwd)"

if [ -d ".venv-lucy-voz" ]; then
    source .venv-lucy-voz/bin/activate
else
    echo "Error: No encuentro el entorno virtual .venv-lucy-voz"
    exit 1
fi

# Ejecutar el módulo
python -m lucy_voice.wakeword_listener
