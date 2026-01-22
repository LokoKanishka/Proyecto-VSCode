#!/bin/bash
set -e  # Cortar si hay error

# 1. Ubicarse en el directorio del proyecto (donde está este script)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "📂 Directorio de trabajo: $DIR"
echo "🚀 Iniciando Lucy V3.2 (Full Duplex + RTX 5090)..."

# 2. Configurar PYTHONPATH para que encuentre los módulos src/
export PYTHONPATH="$DIR"

# 3. Buscar el entorno virtual correcto (el que tiene torch/silero)
if [ -d ".venv-lucy-ui" ]; then
    echo "✅ Activando entorno: .venv-lucy-ui"
    # shellcheck disable=SC1091
    source .venv-lucy-ui/bin/activate
elif [ -d ".venv" ]; then
    echo "⚠️  Aviso: Usando .venv (puede faltar torch para interrupción)"
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo "❌ Error Crítico: No encuentro .venv-lucy-ui. Ejecutá install_deps.sh primero."
    exit 1
fi

# 4. Verificar que el motor de audio tenga los permisos correctos
if [ -f "src/engine/voice_bridge.py" ]; then
    python3 -m py_compile src/engine/voice_bridge.py
    echo "✅ Motor de audio verificado."
else
    echo "❌ Error: No encuentro src/engine/voice_bridge.py"
    exit 1
fi

# 5. LANZAR LA INTERFAZ (Main Loop)
# Esto abre la ventana con el botón de micrófono
exec python3 src/gui/main.py
