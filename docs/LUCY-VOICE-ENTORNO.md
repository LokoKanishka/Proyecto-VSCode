# Entorno de voz de Lucy (`lucy_voice/`)

Este documento registra cómo preparar el entorno de voz de Lucy dentro del repo
`Proyecto-VSCode`, de forma reproducible y 100% local.

## Estructura de carpetas

- `lucy_voice/`
  - `requirements.txt`  → lista de dependencias de Python para la parte de voz/agente.
  - `check_env.py`      → script para verificar que las dependencias estén instaladas.
  - `tests/`            → pruebas simples del entorno de voz (a completar más adelante).

## Comandos base (idea general)

> ATENCIÓN: estos comandos son la receta general.
> Más adelante vamos a ir ejecutándolos paso a paso.
> **Por ahora NO hace falta correrlos.**

### 1. Crear y activar entorno virtual para Lucy-voz

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode

python3 -m venv .venv-lucy-voz
source .venv-lucy-voz/bin/activate

pip install --upgrade pip

pip install -r lucy_voice/requirements.txt

