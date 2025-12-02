# Pipeline de voz original (LEGACY)

Este documento resume el sistema de voz original de Lucy, basado en wake word + Pipecat, que ahora se considera **LEGACY**.

## 1. Componentes principales

* **Wake word** con OpenWakeWord (modelo custom "Hola Lucy")
* **Pipeline Pipecat**:

  * nodos para audio de entrada/salida
  * ASR con Faster Whisper
  * LLM vía Ollama
  * TTS con Mimic3
  * VAD
* **Herramientas del sistema** (capturas de pantalla, abrir apps, etc.)
* Scripts `fix_*` para preparar/limpiar el entorno y ajustar modelos ONNX.

## 2. Ubicación en el proyecto

Tras la limpieza, el código del pipeline original se movió a:

* `legacy/old_voice_system-YYYYMMDD-HHMMSS/`

Los nombres exactos pueden variar según la fecha del backup, pero la estructura interna refleja lo que antes vivía en:

* `lucy_voice/`
* scripts `lucy_voice_wakeword.sh`, `lucy_voice_ptt.sh`, etc.
* scripts `fix_lucy_voice_all.sh`, `fix_pipeline_only.sh`, etc.

## 3. Estado actual

* No es el modo de uso recomendado.
* El código se conserva únicamente como:

  * documentación viva del recorrido del proyecto,
  * posible base para re-experimentos con wake word Pipecat,
  * referencia si se quieren recuperar ideas o scripts.

## 4. Relación con Lucy Voz v2 (nodo modular)

El nodo modular de voz retoma la idea general del asistente:

* voz local,
* LLM local,
* herramientas del sistema,

pero con una arquitectura más simple y fácil de mantener, evitando la complejidad del grafo Pipecat y el entrenamiento de wake words ONNX.
