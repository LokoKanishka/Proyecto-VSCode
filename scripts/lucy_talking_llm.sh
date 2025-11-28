#!/usr/bin/env bash
# Script para lanzar Lucy Talking LLM con Mimic3 TTS
set -e

# Cambiar al directorio del proyecto
cd "$HOME/Lucy_Workspace/lucy_talking_llm"

# Activar el entorno virtual
source .venv-talking-llm/bin/activate

# Ejecutar el asistente con el modelo especificado
# Puedes cambiar el modelo aquí si prefieres otro
python app.py --model gpt-oss:20b
