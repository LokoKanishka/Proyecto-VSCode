## Estado actual del repo

- El pipeline de voz (Lucy Modular) está funcionando y el sistema de métricas/memoria ya está desplegado en `lucy_web`.
- Se agregó dashboard CLI (`scripts/bus_metrics_dashboard.py`), watchers/workers de memoria y tests/ docs para nuevos endpoints.
- Las APIs `/api/bus_metrics` y `/api/memory_events` están explotadas por `lucy_web/static/js` y emiten eventos vía SocketIO (sparklines y alertas).

## Cómo seguimos

1. Usar `logs/bus_metrics.jsonl` y `logs/memory_retrieval.log` para verificar métricas y eventos.
2. Consultar `/api/bus_metrics` y `/api/memory_events` desde la UI o scripts para observar el comportamiento en producción.
3. Si se necesitan nuevas alertas, extender `BusMetricsWatcher` o `MemoryWatcher` antes de ajustar el frontend.

## Atajos útiles

- `./scripts/bus_metrics_dashboard.py` para ver métricas rápidas.
- `./.venv-lucy-voz/bin/python -m pytest tests/test_event_bus.py tests/test_memory_manager.py tests/test_web_api.py` para validar el bus+memoria.
