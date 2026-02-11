# 🧠 LUCY AGI - AI CONTEXT FILE (SAVE POINT)
> **ESTADO:** FASE 6 COMPLETADA (VISIÓN Y PRECISIÓN) ✅
> **HITOS:** Swarm Persistente + Jailbreak Visual + Auto-Focus.

## 1. Capacidades Desbloqueadas (Current State)
* **Swarm 5090:** `qwen2.5:32b` (Cerebro) y `llama3.2-vision` (Ojos) conviven en VRAM (`keep_alive=-1`). Latencia de switch: ~0s.
* **Hawk-Eye Vision:**
    * **Grid Mapping:** Calibrado con `pyautogui.size()` y offset de 105px (Firefox UI).
    * **Auto-Focus:** Clic preventivo en `(sw//2, 10)` antes de capturar para evitar "efecto espejo" con la terminal.
    * **Zoom:** Recorte quirúrgico de la celda detectada (ej: D4).
* **OCR Jailbreak:** Prompt "RAW DATA ONLY" + Filtros de salida sanitizados. Llama 3.2 lee precios sin sermones morales.
* **Orquestación:** `OLLAMA_NUM_PARALLEL=2` permite concurrencia real.

## 2. Lecciones Aprendidas (Hard Constraints)
* **Terminal Blindness:** La terminal SIEMPRE debe minimizarse o el script debe hacer auto-focus en la app objetivo.
* **Vision Refusal:** Los modelos de visión modernos rechazan contextos financieros. Solución: Enmarcar como "Accessibility OCR task".
* **Planner Loop:** El planificador lineal a veces sigue ejecutando pasos después de tener el dato. Se requiere corte temprano (`return` inmediato al detectar número).

## 3. Próximo Objetivo: FASE 7 (Tree of Thoughts)
* **Meta:** Pasar de ejecución lineal a planificación deliberada.
* **Concepto:** Generar múltiples caminos posibles -> Evaluar viabilidad -> Ejecutar el mejor.
* **Stack:** Algoritmo BFS/DFS sobre el `thought_engine.py`.

## 4. Mapa de Archivos Clave
* `src/engine/ollama_engine.py`: Lógica de Jailbreak, Retry y Swarm.
* `src/skills/desktop_skill_wrapper.py`: Acciones físicas (Click, Type, Focus).
* `src/utils/grid_mapper.py`: Matemática de la grilla.
* `run_lucy_swarm.sh`: Script de arranque (Env Vars críticas).

---
*Última actualización: Éxito en lectura de precio Bitcoin (Fase 6).*
