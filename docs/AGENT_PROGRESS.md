# Lucy AGI Progress Tracker

**Lee esto primero al iniciar sesión diaria**

Este archivo resume el estado actual y lo que falta implementar según el plan AGI. Actualízalo en cada sesión antes de pushear.

## Estado al 2026-02-01

### Hecho
- Bus asíncrono y enjambre base: `src/core/bus.py`, `src/engine/swarm_runner.py`.
- Manager + memoria SQLite/embeddings: `src/core/manager.py`, `src/memory/memory_manager.py`.
- Watchers básicos (ventanas, recursos, archivos, timer, notificaciones): `src/watchers/`.
- Workers existentes: `SearchWorker` (DDG), `ChatWorker` (Ollama), `CodeWorker` (mock), `VisionWorker` (grilla + LLM), `BrowserWorker` (Playwright pasos fijos/YouTube), `HandsWorker` (clic/tipeo con verificación visual básica), `MemoryWorker`.
- Control de pantalla y grilla: `src/vision/desktop_controller.py`, `src/skills/grid_mapper.py`.
- SearchWorker ahora integra SearXNG + scraping + ranking semántico + retries/citaciones: `src/workers/search_worker.py`.
- CodeWorker ejecuta código en sandbox temporal, lint/test opcional y safety check: `src/workers/code_worker.py`.
- ShellWorker con timeout, blocklist y PTY opcional: `src/workers/shell_worker.py` (registrado en `src/engine/swarm_runner.py`).
- VSCode/Git/Package workers básicos: `src/workers/vscode_worker.py`, `src/workers/git_worker.py`, `src/workers/package_worker.py`.
- Extensión WS mínima para VS Code: `vscode_extension/lucy-agent/`.
- README para la extensión con build/uso: `vscode_extension/lucy-agent/README.md`.
- pytest.ini agregado para evitar legacy/pipecat en CI local: `pytest.ini`.
- Tests OK en `.venv-codex` (40 passed, 2 skipped). Ver último run en sesión actual.
- Planner agrega propuesta/valoración heurística: `src/planners/tree_of_thought.py`.
- ResourceManager puede refrescar uso de GPU desde `nvidia-smi`: `src/resources/resource_manager.py`.
- MemoryWorker ahora soporta backup y construcción FAISS opcional: `src/workers/memory_worker.py`.
- Manager ahora puede priorizar interrupciones y aplicar budget básico por worker: `src/core/manager.py`.
- Pipeline de visión avanzado (OCR + YOLO opcional) integrado en VisionWorker: `src/vision/vision_pipeline.py`, `src/workers/vision_worker.py`.
- BrowserWorker ahora soporta contexto persistente, captura de estado y snapshot accesible: `src/workers/browser_worker.py`.
- Fallback browser → visión conectado (solo screenshot/headless): `src/workers/browser_worker.py`, `src/core/manager.py`, `src/workers/vision_worker.py`.
- Audio en swarm (Ear/Mouth) integrado y activable por env: `src/workers/ear_worker.py`, `src/workers/mouth_worker.py`, `src/engine/swarm_runner.py`.
- Planner ToT con LLM + persistencia del árbol en DB: `src/planners/tree_of_thought_llm.py`, `src/core/manager.py`, `src/memory/memory_manager.py`.
- vLLM server y soporte vLLM en planner/code: `scripts/start_vllm_server.py`, `src/planners/ollama_planner.py`, `src/workers/code_worker.py`.
- VS Code por WebSocket soportado en worker + extensión WS: `src/workers/vscode_worker.py`, `vscode_extension/lucy-agent/`.
- Entrypoint único (swarm como default) con consola integrada y flags de audio/WS: `scripts/run_lucy.py`, `run_lucy.sh`, `src/engine/swarm_runner.py`.
- Gestión VRAM/swapping mejorada: eventos `gpu_usage`, política de presión, unload de modelos inactivos y keep-alive dinámico + LoRA targets: `src/watchers/resource_watcher.py`, `src/core/manager.py`, `src/engine/swarm_manager.py`.
- Visión/Manos/Browser: SoM básico + SAM opcional, click por UIElement y DOM summary en BrowserWorker: `src/vision/vision_pipeline.py`, `src/workers/vision_worker.py`, `src/workers/hands_worker.py`, `src/workers/browser_worker.py`.
- Loader RICO opcional para calibración/datasets: `src/vision/rico_dataset.py`, `src/vision/vision_pipeline.py`.
- Concurrencia distribuida básica: WS gateway con suscripciones + bridge entre buses: `src/core/ws_gateway.py`, `src/core/ws_bus_bridge.py`, `src/engine/swarm_runner.py`.
- Memoria avanzada: backups con política de cifrado, FAISS always-on incremental y resumen jerárquico: `src/memory/memory_manager.py`, `src/workers/memory_worker.py`.
- E2E pipeline (mock): prueba “voz→plan→visión→manos→browser→respuesta” con planner falso: `tests/test_swarm_e2e_pipeline.py`.
- QA: nota para usar `python3` o alias `python-is-python3`: `docs/QA.md`.
- Hardening bridge WS: límite de hops y dedupe simple para evitar loops: `src/core/ws_bus_bridge.py`.
- Trazabilidad: snapshots de archivos persistidos en memoria: `src/memory/memory_manager.py`, `src/workers/memory_worker.py`.
- Bridge WS: backpressure con cola y métricas básicas: `src/core/ws_bus_bridge.py`.
- Snapshots automáticos al escribir archivos (VSCodeWorker): `src/workers/vscode_worker.py`.
- Bridge WS: latencia promedio y backlog máximo en métricas: `src/core/ws_bus_bridge.py`.
- Snapshots automáticos desde CodeWorker (write_file): `src/workers/code_worker.py`.
- Bridge WS: alerta `bridge_backpressure` al superar umbral: `src/core/ws_bus_bridge.py`.
- Tests: snapshot de archivos en memoria cubierto por `tests/test_memory_manager.py`.
- Bridge WS: evento `bridge_stats` periódico con latencia/backlog: `src/core/ws_bus_bridge.py`.
- Bridge WS: stats incluidos en bus_metrics + smoke `scripts/bridge_smoke.sh`: `src/watchers/bus_metrics_watcher.py`, `lucy_web/app.py`, `lucy_web/static/js/resources.js`, `scripts/bridge_smoke.sh`.
- Smokes extra: `scripts/memory_snapshot_smoke.py` y flags en `scripts/run_all_smokes.sh`.
- UI/Docs: bridge stats en UI y `/api/bus_metrics`: `lucy_web/static/js/resources.js`, `docs/LUCY-WEB-API.md`.
- Demo multi-nodo bridge: `scripts/bridge_multi_node_demo.sh`.
- Bridge metrics persistentes + panel UI: `src/core/ws_bus_bridge.py`, `lucy_web/app.py`, `lucy_web/static/js/resources.js`.
- CI smoke script: `scripts/ci_smoke.sh`.
- Bridge: p50/p95, backoff con jitter, multi-URL, control dinámico de tópicos: `src/core/ws_bus_bridge.py`, `src/engine/swarm_runner.py`.
- Bus: métricas de latencia por worker en bus_metrics: `src/core/bus.py`, `src/watchers/bus_metrics_watcher.py`.
- Manager: throttling de eventos ruidosos: `src/core/manager.py`.
- Memoria: rotación de backups + snapshots comprimidos + FAISS reload: `src/memory/memory_manager.py`.
- Visión/Manos/Browser: cache SAM, SoM con label_norm, acciones extra de manos, DOM tables, auto-fallback: `src/vision/vision_pipeline.py`, `src/workers/hands_worker.py`, `src/workers/browser_worker.py`.
- Code/VSCode: límites de contenedor y WS default: `src/workers/code_worker.py`, `src/workers/vscode_worker.py`.
- UI/API: bridge metrics panel + endpoint `/api/bridge_metrics`: `lucy_web/app.py`, `lucy_web/static/js/resources.js`, `docs/LUCY-WEB-API.md`.
- Tests/CI: dom_summary tables + events endpoint + GitHub Actions CI: `tests/test_browser_dom_summary.py`, `tests/test_web_api.py`, `.github/workflows/ci.yml`.
- E2E bridge multi-nodo (in-process): `tests/test_ws_bridge_multi.py`.
- Docs: `docs/SWARM_DISTRIBUTED.md` y `docs/DEPLOY_CHECKLIST.md`.
- Tests: backup requiere cifrado si `LUCY_BACKUP_REQUIRE_ENCRYPTION=1`: `tests/test_memory_manager.py`.
- Smoke remoto multi-host: `scripts/bridge_remote_smoke.sh` (ejecutado en local).
- Fix: import `os` en Manager para throttling de eventos: `src/core/manager.py`.
- Memoria: pruning configurable de eventos por retención/tamaño: `src/memory/memory_manager.py`.
- Browser: cache TTL para `distill_url`: `src/workers/browser_worker.py`.
- Hands: modo `confirm_only` / `LUCY_HANDS_CONFIRM` para acciones: `src/workers/hands_worker.py`.
- Bus: cola durable opcional (JSONL) con replay en start: `src/core/bus.py`.
- Manager: cooldown configurable por worker para evitar thrash: `src/core/manager.py`.
- Swarm: evicción/idle de LoRAs con prune periódico: `src/engine/lora_manager.py`, `src/engine/swarm_manager.py`.
- Memoria: cache persistente de embeddings con invalidación por hash: `src/memory/memory_manager.py`.
- VS Code WS: reintentos con backoff + buffer offline: `src/workers/vscode_worker.py`.
- Telemetría: evento `stage_latency` por etapa en Manager: `src/core/manager.py`.
- Focus ventanas: retry + verificación de ventana activa: `src/vision/desktop_controller.py`.
- Browser: resumen destilado incluye URL como fuente en prompt: `src/core/manager.py`.
- UI/API: panel de latencia por etapa y endpoint `/api/stage_latency`: `lucy_web/app.py`, `lucy_web/static/js/resources.js`, `lucy_web/templates/index.html`, `docs/LUCY-WEB-API.md`.
- Dataset: script de descarga RICO con hash opcional: `scripts/rico_download.sh`, `docs/DATASETS.md`.
- Replay: script para reemitir eventos por WS: `scripts/replay_events.py`.
- CI: smoke headless mínimo: `scripts/ci_headless.sh`.
- Healthcheck extendido + estado DB: `lucy_web/app.py`.
- Estado de workers (last seen): `lucy_web/app.py`, `lucy_web/static/js/resources.js`, `lucy_web/templates/index.html`.
- Logs: rotación simple por líneas: `scripts/rotate_logs.sh`.
- Hands: safe mode por acción: `src/workers/hands_worker.py`.
- Snapshots: retención por tamaño/cantidad: `src/memory/memory_manager.py`.

### Falta (prioriza en cada sesión)
0) **Pendiente menor**: ejecutar `scripts/bridge_remote_smoke.sh` en hosts reales (multi-host).

### Próximas 20 tareas (2026-02-01)
Completadas en esta sesión (20/20): TLS+token WS, métricas de cola/latencia, badge bridge, prioridad por backpressure, export/import snapshots, compresión configurable, cache OCR, heurísticas UIElement, scroll/drag, click_text, metadata OG, tests auto, timeouts env, WS health, E2E bridge opcional, CI matrix+cache, docs distribuido + checklist.

### Ritual diario sugerido
- Leer este archivo y marcar qué punto atacar hoy.
- Actualizar la sección “Hecho/Falta” con cambios concretos (archivos y breve nota).
- Antes de pushear, anota en “Falta” lo pendiente y en “Hecho” lo nuevo.

### Notas rápidas
- Línea base de visión/acciones ya existe pero es mínima. No asumas funcionalidades de detección/OCR.
- Mantener idioma de usuario: español rioplatense en UI/logs visibles.
- Extras de visión instalados en `.venv-codex` (diskcache/pytesseract/opencv/ultralytics/faiss-cpu). Tesseract del sistema requiere `sudo apt install tesseract-ocr`.
- Dependencias principales instaladas en `.venv-codex` (requirements + requirements-web + dev).
- Playwright descargó navegadores en `.venv-codex`, pero faltan libs del sistema (`libicu*`, `libvpx`, `libevent`).
