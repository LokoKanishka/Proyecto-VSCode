#!/usr/bin/env bash

set -e

echo "== Instalación sugerida de dependencias (Ubuntu) =="
echo
echo "Este script NO instala nada automáticamente."
echo "Solo muestra un comando sugerido para que lo revises y lo pegues vos."
echo

cat << 'CMD'
sudo apt update
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    python3 \
    python3-pip \
    nodejs \
    npm \
    docker.io \
    docker-compose
CMD

echo
echo "Revisá el comando de arriba."
echo "Si estás de acuerdo, copialo y ejecutalo manualmente en la terminal."
