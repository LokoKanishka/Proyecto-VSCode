#!/bin/bash
echo "⚡ Iniciando Protocolo Lucy v2..."

# 1. Configurar PYTHONPATH para que 'src.core' sea visible desde la raíz
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 2. Limpieza de procesos previos de Ray (Higiene)
echo "🧹 Limpiando procesos antiguos de Ray..."
ray stop > /dev/null 2>&1
rm -rf /tmp/ray

# 3. Lanzar el cerebro (Ray se iniciará automáticamente dentro del script)
echo "🧠 Despertando al Enjambre..."
python3 -u src/core/lucy_boot.py swarm
