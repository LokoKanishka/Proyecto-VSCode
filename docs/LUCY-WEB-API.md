# Lucy Web UI - API y dashboard

Este documento registra los endpoints HTTP que provee `lucy_web/app.py` y el script asociado para visualizar métricas del bus que conecta los workers de Lucy.

## Endpoints disponibles

### `/api/bus_metrics`
Devuelve las últimas métricas recabadas por `BusMetricsWatcher` (`logs/bus_metrics.jsonl`), incluyendo totales de mensajes publicados/despachados, respuestas y errores. El payload tiene dos claves:

- `records`: lista de registros recientes (cada uno contiene `timestamp` y `metrics`).
- `summary`: describe el `summary` calculado para los últimos 10 registros (`latest`, `avg`, `min`, `max`) y también redispara esa lista (`recent`).

Este endpoint se usa en la UI para mostrar un panel de métricas del bus y alimentar el script `scripts/bus_metrics_dashboard.py`.

### `/api/memory_events`
Expone los eventos de recuperación semántica registrados por `MemoryWatcher` (`logs/memory_retrieval.log`). Cada línea del log se convierte en un objeto con:

- `timestamp`: la marca de tiempo ISO.
- `details`: texto generado por el watcher (por ejemplo `retrieved_memory #3: 2 items`).

Si la línea no puede separarse por `|`, el mapa contiene `raw`.

### `/api/resource_events` y `/api/plan_log`
Ya existían previamente; la UI consumía `/api/resource_events` para información de GPU/ventanas y `/api/plan_log` para mostrar el último plan ejecutado. Nada se modifica en ellos en esta iteración.

## Script de dashboard (`scripts/bus_metrics_dashboard.py`)

El script lee `logs/bus_metrics.jsonl`, calcula promedios (`avg/min/max`) y muestra los últimos 5 registros en consola. Sirve para tener un monitoreo rápido fuera de la UI. Se ejecuta así:

```
./scripts/bus_metrics_dashboard.py
```

El script no depende de Flask y puede correrse en segundo plano (por ejemplo, combinado con `watch` o en un `tmux`).

## Consideraciones

- Las APIs de métricas y memoria son **seguras** para llamar sin que existan los archivos de log: respondan con estructuras vacías para no romper la UI.
- También se actualizó el frontend (`lucy_web/static/js/resources.js`) para refrescar estas fuentes cada 15–25 segundos y mostrar un historial visual.  
