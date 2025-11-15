#!/usr/bin/env bash

set -e

echo "== Verificando dependencias =="

deps=(git curl wget gcc python3 node docker ollama)

for dep in "${deps[@]}"; do
    if command -v "$dep" >/dev/null 2>&1; then
        echo "[OK] $dep encontrado"
    else
        echo "[FALTA] $dep NO está instalado"
    fi
done
