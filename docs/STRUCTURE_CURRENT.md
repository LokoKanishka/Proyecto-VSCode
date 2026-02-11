# Estructura del Repositorio (Consolidada 2026-02-10)

Esta es la organización oficial del proyecto tras la fase de limpieza y estandarización.

## Paquetes Principales
- **`lucy_agents/`**: Lógica de agentes de alto nivel, conectores de ChatGPT, búsqueda y enrutamiento de acciones. (Reemplaza a gran parte de `src/workers/`).
- **`lucy_voice/`**: Motor modular de voz (ASR, TTS, LLM local). (Migrado desde `src/senses/audio/`).
- **`src/`**: Núcleo del sistema Ray.
    - `src/core/`: Bus de eventos, manager de actores y tipos base.
    - `src/engine/`: Orquestación y motores de pensamiento (DFS).
    - `src/senses/`: Sensores de visión y acción de bajo nivel.

## Entrypoints y Lanzadores
- **`run_lucy.sh`**: Ejecuta Lucy en modo estándar.
- **`run_lucy_ray_swarm.sh`**: Lanza el enjambre de actores basado en Ray (Anteriormente `run_lucy_swarm.sh`).
- **`scripts/run_event_swarm.sh`**: Lanza el motor de swarm basado en EventBus (Anteriormente `scripts/run_swarm.sh`).

## Archivo y Experimentos
- **`archive/`**: Contiene backups históricos y archivos `.bak`.
- **`experiments/`**: Contiene prototipos UI y experimentos visuales (como el proyecto "Alt Figurita").
- **`legacy/`**: Sistemas antiguos preservados para referencia (como el viejo pipeline de Pipecat).

## Reglas de Mantenimiento
1. **No crear archivos en la raíz**: Mantener la raíz limpia para lanzadores y configs globales.
2. **Nuevos Workers**: Deben seguir el patrón de `lucy_agents` si son herramientas de alto nivel, o `src/senses` si son integraciones de hardware/sensores.
