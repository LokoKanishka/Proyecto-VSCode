#!/bin/bash
# Script to install OpenWakeWord dependencies specifically for Python 3.12/Linux
# Avoids tflite-runtime issues by using onnxruntime backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv-lucy-voz"

echo "🎤 Installing Wake Word dependencies for Python 3.12..."

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Step 1: Upgrading pip..."
pip install -U pip wheel

echo "Step 2: Installing core dependencies..."
# Core ONNX runtime avoids need for tflite
pip install onnxruntime

echo "Step 3: Installing openwakeword (no deps mode)..."
# We install with --no-deps to avoid tflite-runtime constraint validation failure
pip install --no-deps openwakeword>=0.5.0

echo "Step 4: Verifying installation..."
python3 -c "import openwakeword; import onnxruntime; print('✅ OpenWakeWord + ONNX Runtime installed successfully')"

echo ""
echo "🎉 Installation complete. Wake word ready."
