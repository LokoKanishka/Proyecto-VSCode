# Módulos legacy y laboratorio (fuera del flujo de Lucy Voz v2)

Lucy Voz v2 se ejecuta con el **nodo de voz modular** en `external/nodo-de-voz-modular-de-lucy`, el lanzador oficial `scripts/lucy_voice_modular_node.sh`, los agentes en `lucy_agents/` y el web agent en `lucy_web_agent/`, más la configuración principal (`config.yaml`, `lucy.desktop`, docs vivas). Este archivo documenta los módulos que hoy **no forman parte del flujo activo** y se conservan solo como referencia o laboratorio.

## 1. Módulos totalmente legacy (pipeline viejo de voz)

- `legacy/` contiene el pipeline anterior basado en Pipecat + wake word ONNX.
- No se usa más en el flujo actual del nodo modular y se mantiene únicamente como referencia histórica o base para experimentos.

## 2. Archivos de respaldo

- `docs/backup/` guarda backups automáticos de README/config.
- No es necesario para ejecutar Lucy Voz v2 ni para el flujo del nodo modular.

## 3. Experimentos web no usados por Lucy Voz v2

- `lucy_web/` reúne código web y herramientas auxiliares experimentales que hoy no están en el circuito del nodo de voz modular.
- Se mantiene como laboratorio; puede moverse a otro repo o carpeta separada en el futuro sin afectar el flujo actual.

## 4. Scripts de migración

- `scripts/cleanup_old_voice_system.sh` fue un script de limpieza del sistema de voz viejo (Pipecat + wake word).
- No se ejecuta como parte del flujo normal de Lucy Voz v2.
