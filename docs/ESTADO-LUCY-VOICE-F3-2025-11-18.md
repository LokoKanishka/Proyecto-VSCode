# Lucy Voz – Estado F3 – 18/11/2025

## 1. Contexto y posición dentro del proyecto

Este archivo deja constancia de en qué estado está **Lucy Voz** al 18/11/2025,
dentro del proyecto general **Proyecto-VSCode**.

- Fase 1 (entorno de voz instalado y probado) → **completada**.
- Fase 2 (pipeline manual mic → ASR → LLM → TTS) → **completada y documentada** en  
  `docs/ESTADO-LUCY-VOICE-F2-2025-11-16.md`.
- Fase 3 comienza acá con:
  - modo voz **push-to-talk**,
  - comando de apagado por voz **“Lucy desactivate”**,
  - TTS ajustado a una voz de Mimic 3 estable,
  - primer prototipo de **wake word** usando openWakeWord,
  - integración inicial con un stub de Pipecat.

---

## 2. Cambios principales desde el estado F2

### 2.1. TTS estabilizado (Mimic 3 → WAV → aplay)

En Fase 2 se había probado la voz `es_ES/carlfm_low`, pero en la práctica
producía audios muy cortos o débiles.  
En Fase 3 se consolida el siguiente camino:

- Voz de Mimic 3: `es_ES/m-ailabs_low` (gallego en castellano, clara y estable).
- Método interno: `_speak_with_tts(text: str)` en `pipeline_lucy_voice.py`.
- Flujo:
  1. Ejecuta `mimic3 --voice es_ES/m-ailabs_low --stdout`.
  2. Envía el texto por `stdin`.
  3. Guarda el resultado en `/tmp/lucy_tts_runtime.wav`.
  4. Reproduce con `aplay /tmp/lucy_tts_runtime.wav`.

Esta ruta está probada escuchando la salida real desde los parlantes.

### 2.2. Roundtrip con apagado por voz

El método clave sigue siendo:

```python
run_mic_llm_roundtrip_once(duration_sec: float = 5.0) -> bool
