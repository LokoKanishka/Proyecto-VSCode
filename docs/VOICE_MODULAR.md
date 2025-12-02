
# Lucy Voz v2 - Nodo de voz modular

Este documento describe el estado actual del nodo de voz modular de Lucy, que reemplaza al pipeline original con wake word + Pipecat como **modo principal** de uso.

## 1. Objetivo

* Proveer un asistente de voz local, manos libres, basado en:

  * Whisper (ASR)
  * Ollama (LLM)
  * Mimic3 (TTS)
  * VAD con `webrtcvad`

## 2. Flujo de ejecución

1. Lanzador: `scripts/lucy_voice_modular_node.sh`

2. El script:

   * activa `.venv-lucy-voz`
   * entra en `external/nodo-de-voz-modular-de-lucy`
   * ejecuta `python app.py` (por defecto en CPU, con `CUDA_VISIBLE_DEVICES=""`)

3. `app.py`:

   * inicializa ASR, TTS y LLM
   * muestra parámetros iniciales (voz, emotion, CFG, modelo LLM)
   * espera que el usuario presione **Enter** una vez
   * entra en el bucle:

     * escucha audio hasta silencio (VAD)
     * transcribe con Whisper
     * decide si la transcripción es un comando de cierre ("lucy dormi", etc.)
     * consulta al LLM y sintetiza respuesta con Mimic3
     * vuelve a escuchar

## 3. Comando de sueño

En el nodo modular se implementa una función del estilo:

* normaliza el texto a minúsculas
* elimina tildes
* busca coincidencias con frases configuradas (por ejemplo `"lucy dormi"`)

Si el comando aparece:

* imprime un mensaje de confirmación
* sale del bucle principal
* cierra la sesión de voz

La lista de comandos de cierre debería coordinarse con `config.yaml` bajo la clave `voice_modular.sleep_commands`.

## 4. Parámetros típicos

* Modelo Whisper: `base` (puede cambiarse a `small`, `medium`, etc.)
* Modelo LLM (Ollama): `gpt-oss:20b`
* Voz Mimic3: `es_ES/m-ailabs_low`
* `Emotion exaggeration`: `0.5`
* `CFG weight`: `0.5`
* Sample rate: `16000` Hz
* `vad_aggressiveness`: valor entre 0–3 (más alto = más agresivo)

Estos parámetros pueden fijarse en `config.yaml` y/o directamente en `app.py`. Lo ideal es ir migrándolos a config centralizada.

## 5. Pendientes / ideas de mejora

* Afinar la detección del comando de sueño para evitar falsos positivos.
* Centralizar toda la configuración en `config.yaml`.
* Agregar logs más detallados de cada turno (tiempos, tokens, etc.).
* Ajustar las voces y parámetros de Mimic3 para lograr una personalidad más marcada de Lucy.
  EOF

cat > docs/LEGACY_VOICE_PIPELINE.md << "EOF"

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

