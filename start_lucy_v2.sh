#!/bin/bash
echo "⚡ Iniciando Protocolo Lucy v2..."

# 1. Configurar PYTHONPATH para que 'src.core' sea visible desde la raíz
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 2. Verificar e iniciar Ray si no está corriendo
if ! ray status > /dev/null 2>&1; then
    echo "🟡 Ray no detectado. Iniciando nodo local..."
    ray start --head --disable-usage-stats
else
    echo "🟢 Ray ya está activo."
fi

# 3. Lanzar el cerebro (usando la ruta correcta detectada: src/core/lucy_boot.py)
echo "🧠 Despertando al Enjambre..."
python3 src/core/lucy_boot.py swarm
