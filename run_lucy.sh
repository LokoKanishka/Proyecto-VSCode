#!/bin/bash
export PYTHONPATH=/home/xdie/Proyecto-VSCode
echo "🚀 Verificando sintaxis..."
if .venv/bin/python3 -m py_compile src/engine/voice_bridge.py; then
    echo "✅ Código Válido. Ejecutando..."
    .venv/bin/python3 src/gui/main.py
else
    echo "❌ ERROR FATAL DE SINTAXIS. Revisa el copiado/pegado."
    read -p "Presiona Enter para salir..."
fi
