#!/bin/bash
set -e

# Build script for vLLM on RTX 5090 (Blackwell)
# Requires: Copious RAM and CUDA Toolkit 12.8+ available in path

echo "🚀 Starting vLLM build for Blackwell..."

# Clone if not exists
if [ ! -d "vllm" ]; then
    git clone https://github.com/vllm-project/vllm.git
    cd vllm
else
    cd vllm
    git pull
fi

# Set build flags for Blackwell (SM120)
# Note: As of early 2025/2026, SM120 might need specific enabling in modern PyTorch.
# We set 9.0 (Hopper) and enable forward compatibility.
export TORCH_CUDA_ARCH_LIST="9.0+PTX" 
export MAX_JOBS=12
export NVCC_THREADS=12

# Install build dependencies
pip install -r requirements-build.txt

# Build and Install
echo "🔨 Compiling..."
pip install -e .

echo "✅ vLLM installation complete."
