# Browser Agent avanzado

Este documento explica los nuevos mecanismos que hacen que el BrowserWorker sea un agente robusto con DOM distillation, login persistente y distiller Ray-friendly.

## 1. Objetivos

1. **DOM distillation ligera:** el manager no procesa HTML crudo; el worker usa Ray (`src/core/ray_manager.py`) para resumir títulos, enlaces y tablas y entrega un payload `dom_access`.
2. **Persistencia de cookies:** cada dominio opera con un archivo `cache/browser_states/<dominio>.json`. Si la página necesita login (ChatGPT, Gemini), se carga el storage state previo, se interactúa y se guarda al cerrar.
3. **Fallback Ray:** si `ray` no está disponible, la distilación usa BS4 directamente.

## 2. Flujo de ejecución

- Antes de crear un contexto Playwright, se calcula la ruta de storage state (`_storage_state_for_url`). Si existe, se pasa a `context.new_context(storage_state=...)`.  
- Tras cada lote de pasos, se obtiene `page.content()` y se transmite a `distill_dom_ray` para obtener el resumen estructurado (headings/links/tables).  
- Al final de la ejecución se almacena el DOM summary en `dom_access` y se devuelve junto con `storage_state`.

## 3. Cómo usarlo

- `message.data` puede incluir `url` para dominar, `steps` con acciones Playwright, y opcionalmente `fallback_vision`.  
- Las respuestas contienen `dom_access` (JSON) y `storage_state`. Para replicar un login persistente se pasa el mismo `url` en ejecución posteriores.

## 4. Ray / Prometheus

- El actor `DomDistillerActor` (`src/core/ray_manager.py`) corre en Ray y expone `distill(html)`. Esta tarea incrementa el contador `lucy_dom_tasks_total` y exponemos `lucy_ray_tasks_in_flight`.  
- Si Ray no está instalado, se usa `_local_distill` sin Ray.  
- El endpoint `/metrics` en `lucy_web/app.py` permite que Prometheus raspe los histogramas y contadores.

