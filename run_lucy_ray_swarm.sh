#!/bin/bash
# Lucy Ray Swarm - Optimizado para recursos del sistema
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${LUCY_OLLAMA_HOST:-http://localhost:11434}"
MAIN_MODEL="${LUCY_MAIN_MODEL:-qwen2.5:32b}"
VISION_MODEL="${LUCY_VISION_MODEL:-llama3.2-vision}"

export LUCY_MAIN_MODEL="$MAIN_MODEL"
export LUCY_VISION_MODEL="$VISION_MODEL"
export LUCY_SWARM_PERSIST="${LUCY_SWARM_PERSIST:-1}"
export LUCY_SWARM_KEEP_ALIVE="${LUCY_SWARM_KEEP_ALIVE:--1}"

# Optimización de paralelismo según hardware
# Detectar CPU cores disponibles
CPU_CORES=$(nproc 2>/dev/null || echo "4")
PARALLEL_MODELS=$(( CPU_CORES / 4 ))
[[ $PARALLEL_MODELS -lt 1 ]] && PARALLEL_MODELS=1
[[ $PARALLEL_MODELS -gt 2 ]] && PARALLEL_MODELS=2

export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-$PARALLEL_MODELS}"
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-$PARALLEL_MODELS}"
export LUCY_MAX_TOOL_ITERATIONS="${LUCY_MAX_TOOL_ITERATIONS:-8}"

echo "⚙️ CPU Cores detectados: $CPU_CORES"
echo "🧠 Modelos paralelos: $OLLAMA_NUM_PARALLEL"
echo "🧠 Swarm host: $HOST"
echo "🧠 Main model: $MAIN_MODEL"
echo "👁️ Vision model: $VISION_MODEL"

if [[ "${LUCY_RESTART_OLLAMA:-0}" == "1" ]]; then
  if command -v systemctl >/dev/null 2>&1; then
    echo "🧹 Reiniciando Ollama..."
    sudo systemctl restart ollama
    sleep 2
  else
    echo "⚠️ systemctl no disponible, salto reinicio."
  fi
fi

echo "🔥 Precargando modelos en VRAM..."
curl -s -X POST "$HOST/api/chat" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MAIN_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"stream\":false,\"keep_alive\":-1}" \
  >/dev/null || true

curl -s -X POST "$HOST/api/chat" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$VISION_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"stream\":false,\"keep_alive\":-1}" \
  >/dev/null || true

PYTHON_BIN=".venv_web/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

echo "🤖 Iniciando Lucy (recursos optimizados)..."
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
exec "$PYTHON_BIN" src/main.py
