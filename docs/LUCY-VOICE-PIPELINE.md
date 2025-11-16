# Lucy voz – Fase 2: Pipeline y encastre (borrador inicial)

Este documento describe la Fase 2 del proyecto de Lucy voz: el encastre de todas las piezas
(TTS, ASR, wake word, LLM y herramientas) en un solo pipeline orquestado con Pipecat.

## Objetivo general

Conectar todo en un flujo continuo:

“hola Lucy” → escucha → transcribe → piensa (LLM) → opcionalmente actúa (LucyTools) → responde con voz,

respetando siempre las reglas del proyecto (open-source, local, sin costo y cambios seguros).

## Bloques de trabajo de la Fase 2

1. **Pipeline de audio + wake word + ASR en Pipecat**
   - Nodos básicos:
     - entrada de micrófono (stream),
     - módulo de wake word (OpenWakeWord),
     - módulo de VAD (detección de fin de frase),
     - módulo de ASR (faster-whisper).
   - Resultado: cuando se dice “hola Lucy” y se habla, queda un texto transcrito listo para el LLM.

2. **Integración del LLM en Ollama**
   - Conectar la salida de ASR a un nodo LLM en Pipecat (Ollama).
   - Usar un modelo rápido para voz en tiempo real.
   - Mantener `gpt-oss:20b` como modelo pesado de referencia para tareas más profundas.

3. **Integración del TTS**
   - Conectar la salida del LLM a Mimic 3 (y luego XTTS-v2).
   - Probar el ciclo completo:
     “hola Lucy, ¿qué hora es?” → respuesta hablada.

4. **Half-duplex (no hablar y escuchar al mismo tiempo)**
   - Cuando el TTS está hablando:
     - pausar wake word + ASR.
   - Cuando el TTS termina:
     - reactivar wake word + ASR.
   - Manejar esto con flags/estado dentro del orquestador Pipecat.

5. **Tool Calling + LucyTools**
   - Definir esquemas JSON de herramientas para el LLM (abrir aplicaciones, capturas, etc.).
   - Pipecat ejecuta `lucy_tools.py` cuando el LLM pide una herramienta y luego le devuelve el
     resultado para que lo explique por voz.

6. **GUI mínima (prototipo)**
   - Una interfaz simple (por ejemplo con Gradio) que muestre:
     - historial de texto (usuario / Lucy),
     - estado actual del pipeline (listening / thinking / speaking / herramienta).

## Estado actual al iniciar la Fase 2

- Fase 1 completada:
  - Entorno `lucy_voice/` creado y versionado.
  - Tests individuales de:
    - TTS (Mimic 3),
    - ASR (faster-whisper),
    - wake word (OpenWakeWord),
    - Pipecat (import básico),
    - LucyTools (captura de pantalla).
- Agente de VS Code configurado con modelos locales vía Ollama (principal: gpt-oss:20b),
  respetando las reglas de `AGENTS.md`.

## Próximo paso previsto

El siguiente paso técnico (2.2) será crear un archivo Python base del pipeline de Pipecat
dentro de `lucy_voice/`, solo con la estructura vacía del grafo (sin lógica compleja),
para empezar a conectar micrófono → ASR → LLM → TTS de manera incremental.
