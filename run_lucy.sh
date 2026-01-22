#!/bin/bash

echo "🔋 Iniciando Protocolo Lucy..."

# 1. Asegurar Audio
echo "🔊 Verificando PulseAudio..."
if ! pactl info > /dev/null 2>&1; then
    pulseaudio --start
    echo "   ✅ PulseAudio reiniciado."
else
    echo "   ✅ Audio OK."
fi

# 2. Configurar Entorno
export PYTHONPATH=$(pwd)
source .venv/bin/activate

# 3. Lanzar
echo "🚀 Ejecutando Interfaz..."
python3 src/gui/main.py
