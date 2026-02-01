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

### Falta (prioriza en cada sesión)
1) **Visión avanzada**: ajustar modelos/datasets (YOLOv8/SAM), calibrar morfología y grafo de conectividad; validar resultados reales en pantalla.
2) **Búsqueda robusta**: validar en entorno real y ajustar configuración vía `config.yaml`.
3) **BrowserWorker**: completar fallback visión/DOM inteligente y scripts para Gemini/ChatGPT; logging más detallado.
4) **Code/Chat Workers**: robustecer aislamiento (sandbox real), delegación avanzada y soporte LoRA estable.
5) **Planner ToT real**: generación/valoración de ramas, persistencia de nodos, etiquetas seguro/maybe/imposible, límites de coste.
6) **Gestión de recursos**: monitor VRAM/`nvidia-smi`, carga/descarga dinámica de modelos/LoRAs, reducción de contexto cuando hay presión.
7) **Memoria avanzada**: backups/cifrado, FAISS real, resúmenes jerárquicos, uso de tablas `files/plan_logs` para trazabilidad de código.
8) **Watchers → interrupción**: priorización/throttle y puente al planner para pausar tareas en eventos críticos.
9) **IDE/terminal**: compilar/instalar extensión WS de VS Code y mejorar `ShellWorker` con pexpect/PTY, manejo seguro de comandos y validación avanzada.
10) **Seguridad/Sandbox**: fortalecer aislamiento; hoy hay blocklist básica en Shell/Code pero falta auditoría cifrada y contenedores.

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
