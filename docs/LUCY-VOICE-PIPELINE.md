# Lucy voz – Fase 2: Pipeline y encastre

Este documento describe la Fase 2 del proyecto de Lucy voz: el encastre de todas las piezas
(TTS, ASR, wake word, LLM y herramientas) en un solo pipeline orquestado con Pipecat.

## Objetivo general

Conectar todo en un flujo continuo:

“hola Lucy” → escucha → transcribe → piensa (LLM) → opcionalmente actúa (LucyTools) → responde con voz,

respetando siempre las reglas del proyecto (open-source, local, sin costo y cambios seguros).

## Bloques de trabajo de la Fase 2

1. **Pipeline de audio + wake word + ASR en Pipecat**
   - entrada de micrófono (stream)
   - módulo de wake word (OpenWakeWord)
   - módulo de VAD (detección de fin de frase)
   - módulo de ASR (faster-whisper)
   - Resultado: cuando se dice “hola Lucy” y se habla, queda un texto transcrito listo para el LLM.

2. **Integración del LLM en Ollama**
   - Conectar la salida del ASR a un nodo LLM en Pipecat (Ollama).
   - Usar un modelo rápido para voz en tiempo real.
   - Mantener `gpt-oss:20b` como modelo pesado de referencia para tareas más profundas.

3. **Integración del TTS**
   - Conectar la salida del LLM a Mimic 3 (y luego XTTS-v2).
   - Probar el ciclo completo: “hola Lucy, ¿qué hora es?” → respuesta hablada.

4. **Half-duplex (no hablar y escuchar al mismo tiempo)**
   - Cuando el TTS está hablando: pausar wake word + ASR.
   - Cuando el TTS termina: reactivar wake word + ASR.
   - Manejar esto con flags/estado dentro del orquestador Pipecat.

5. **Tool Calling + LucyTools**
   - Definir esquemas JSON de herramientas para el LLM (abrir aplicaciones, capturas, etc.).
   - Pipecat ejecuta `lucy_tools.py` cuando el LLM pide una herramienta y luego le devuelve
     el resultado para que lo explique por voz.

6. **GUI mínima (prototipo)**
   - Interfaz simple (por ejemplo con Gradio) que muestre:
     - historial de texto (usuario / Lucy)
     - estado actual del pipeline (listening / thinking / speaking / herramienta).

## Estado al iniciar la Fase 2

- Entorno `lucy_voice/` creado y versionado.
- Tests individuales de:
  - TTS (Mimic 3)
  - ASR (faster-whisper)
  - wake word (OpenWakeWord)
  - Pipecat (import básico)
  - LucyTools (captura de pantalla).
- Agente de VS Code configurado con modelos locales vía Ollama (principal: `gpt-oss:20b`),
  respetando las reglas de `AGENTS.md`.

---

## Estado actualizado (16/11/2025)

Además de lo anterior, ahora Lucy voz tiene:

- Un módulo `LucyVoicePipeline` en `lucy_voice/pipeline_lucy_voice.py`.
- Un método `run_text_roundtrip()` que llama al modelo local en Ollama (`gpt-oss:20b`)
  y devuelve una respuesta breve como Lucy en castellano rioplatense.
- Un modo de chat en consola (`interactive_loop()`), ejecutable con:

  ```bash
  python -m lucy_voice.pipeline_lucy_voice
