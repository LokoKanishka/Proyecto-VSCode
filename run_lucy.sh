#!/bin/bash
echo "🔋 Iniciando Protocolo Lucy (v1.0-STABLE)..."

# 1. Revivir Audio si está muerto
if ! pactl info > /dev/null 2>&1; then
    echo "🔊 Reiniciando PulseAudio..."
    pulseaudio --start
else
    echo "✅ Audio OK"
fi

# 2. Configurar Entorno
export PYTHONPATH=/home/xdie/Proyecto-VSCode
source .venv/bin/activate

# 3. Lanzar App
echo "🚀 Ejecutando..."
python3 src/gui/main.py
