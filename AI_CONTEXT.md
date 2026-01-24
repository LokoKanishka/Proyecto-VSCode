# LUCY AGI - AI CONTEXT FILE
> IMPORTANTE: leer este archivo al inicio de cada sesion. Contiene el estado real del proyecto y decisiones clave.

## 1. Identidad del Proyecto
- Nombre: Lucy AGI (agente de escritorio local).
- Hardware: RTX 5090 (32GB VRAM), Ryzen 9, 128GB RAM.
- OS: Ubuntu Linux (X11).
- Filosofia: 100% local, privacidad total, action-first (actuar antes de narrar).

## 2. Stack Actual (2026-01-24)
- Orquestador: Python, monolito en `src/main.py` (modo voz o texto).
- Cerebro (texto): Swarm Mode. Main: `qwen2.5:14b`.
- Ojos (vision): `llama3.2-vision` (Swarm Mode).
- Oido (ASR): Whisper + Silero VAD.
- Boca (TTS): Mimic3 (local).
- Manos (accion): PyAutoGUI (teclado, mouse, screenshots).

## 3. Estado por Fases
| Fase | Nombre | Estado | Logros |
| --- | --- | --- | --- |
| 1 | Sentidos basicos | OK | Whisper + Mimic3 operativos. |
| 2 | Cerebro local | OK | OllamaEngine integrado. |
| 3 | Cuerpo digital | OK | Acciones fisicas en escritorio. |
| 4 | Memoria & grounding | OK | Buffer de investigacion + grilla visual + limpieza de memoria. |
| 5 | Swarm / model swapping | OK | Swapping dinamico (keep_alive), latencia ~2s, gestion de VRAM. |

## 4. Archivos Clave
- `src/main.py`: punto de entrada (voz o texto).
- `src/engine/ollama_engine.py`: motor principal (tools, memoria, vision).
- `src/engine/swarm_manager.py`: gestiona perfiles de modelos (general/vision).
- `src/skills/desktop_skill_wrapper.py`: acciones y captura de pantalla.
- `src/skills/research_memory.py`: memoria corta de investigacion.
- `config.yaml`: configuracion central (modelos, voz, VAD, etc).

## 5. Decisiones Tecnicas (No Cambiar sin Motivo)
1. Accion primero: si el usuario pide hacer, se ejecuta antes de hablar.
2. Scroll fisico: `pagedown` / `pageup` en vez de scroll por pixeles.
3. Vision con grilla: usar `capture_screen(overlay_grid=true)` y clicks por coordenadas (A1..H10).
4. Memoria de investigacion: solo via tool `remember`, no auto-guardar por defecto.

## 6. Swarm Manager (Resumen)
- `SwarmManager` usa Ollama `/api/chat` con `keep_alive` para cargar/descargar modelos.
- Perfiles: `general` (mantiene main, descarga vision) y `vision` (mantiene vision, descarga main).
- Modelos configurables:
  - `LUCY_MAIN_MODEL` o `LUCY_OLLAMA_MODEL` (main).
  - `LUCY_VISION_MODEL` o `ollama_vision_model` en `config.yaml` (vision).
  - `LUCY_OLLAMA_HOST` o `ollama_host` (host).

## 7. Proximo Paso (To-Do)
- [ ] Validar swaps reales de VRAM (logs de switch y sin OOM).
- [ ] Ajustar modelos por defecto si se decide `qwen2.5:14b`.
- [ ] Tests manuales completos: vision + remember + resumen final.

Ultima actualizacion: 2026-01-24
