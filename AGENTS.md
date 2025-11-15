# Instrucciones para agentes y herramientas en VS Code

Este archivo define cómo deben trabajar los agentes (por ejemplo, Continue u otros)
cuando interactúan con este repositorio.

## 1. Objetivo general

- Este repo describe y automatiza mi entorno de trabajo en VS Code + Ollama.
- Los agentes deben:
  - Ayudar a mantener estos scripts y documentación.
  - Sugerir mejoras sin borrar ni romper configuraciones existentes.
  - Respetar la preferencia por herramientas open source, locales y sin costo.

## 2. Reglas para modificar archivos

- No modificar archivos fuera de este repo.
- No borrar scripts existentes sin antes proponer una alternativa clara.
- Antes de cambiar un archivo grande, proponer el cambio en secciones pequeñas.

## 3. Uso de scripts

- `scripts/check_deps.sh` se usa solo para verificar dependencias.
- `scripts/install_deps.sh` solo muestra comandos sugeridos; la ejecución siempre es manual.

## 4. Futuras integraciones

- Cuando se agreguen n8n, Databricks u otros servicios, se documentarán aquí:
  - Qué hace cada integración.
  - Qué archivos puede tocar cada agente.
  - Qué comandos están permitidos.
