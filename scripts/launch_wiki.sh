#!/bin/bash

# --- CONFIGURACIÓN DE MISIÓN: WIKIPEDIA ---

# 1. Cerebro y Visión (El modelo que funciona)
export LUCY_VISION_MODEL="qwen2.5vl:7b"
export LUCY_OLLAMA_TIMEOUT=480
export LUCY_MAX_TOOL_ITERATIONS=15
export LUCY_LOG_LEVEL=DEBUG

# 2. Configuración de Ojos y Manos
export LUCY_CAPTURE_ACTIVE_WINDOW=1
export LUCY_FOCUS_WAIT_S=0.8       # Pausa para que no se ponga negra la pantalla
export LUCY_UI_WAIT_S=2.0          # Espera a que cargue la página
export LUCY_FOCUS_CLICK=1          # Click de seguridad para traer foco

# 3. Objetivo: Firefox
export LUCY_BROWSER_BIN="firefox"
export LUCY_FOCUS_APP="Navigator.firefox_firefox"

# 4. Ejecución
cd ~/Lucy_Workspace/Proyecto-VSCode
echo "🧠 Cargando Lucy con Qwen2.5-VL..."
echo "🎯 Objetivo: Wikipedia"
./.venv-lucy-voz/bin/python src/main.py
