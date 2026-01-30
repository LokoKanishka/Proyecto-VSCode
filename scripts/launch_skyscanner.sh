#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Configuración del Cerebro (Paciencia y Visión)
export LUCY_OLLAMA_TIMEOUT=480
export LUCY_VISION_TIMEOUT_S=120
export LUCY_VISION_MODEL="qwen2.5vl:7b"
export LUCY_MAX_TOOL_ITERATIONS=15
export LUCY_LOG_LEVEL=DEBUG

# 2. Configuración del Cuerpo (Ojos y Manos)
export LUCY_CAPTURE_ACTIVE_WINDOW=1
export LUCY_FOCUS_WAIT_S=1.0
export LUCY_UI_WAIT_S=3.0
export LUCY_FOCUS_CLICK=1

# 3. Identidad del Objetivo (Firefox)
export LUCY_BROWSER_BIN="firefox"
export LUCY_FOCUS_APP="Navigator.firefox_firefox"

# 4. Abrir Skyscanner y dar un pequeño margen
firefox --new-window "https://www.skyscanner.com/" >/dev/null 2>&1 &
sleep 4

# Maximizar Firefox para evitar vista móvil
if command -v wmctrl >/dev/null 2>&1; then
  for _ in {1..10}; do
    if wmctrl -lx | grep -qi "firefox"; then
      wmctrl -a "Mozilla Firefox" >/dev/null 2>&1 || true
      wmctrl -x -a "Navigator.firefox_firefox" >/dev/null 2>&1 || true
      wmctrl -r "Mozilla Firefox" -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
      wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
      break
    fi
    sleep 0.5
  done
fi

# 5. Ejecutar Lucy
./.venv-lucy-voz/bin/python src/main.py
