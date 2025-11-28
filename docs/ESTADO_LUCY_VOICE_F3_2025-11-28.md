# Estado Lucy Voice F3 – 2025-11-28

## Correcciones aplicadas hoy
- Secuencialidad LLM/TTS: `OllamaLLMProcessor` ahora serializa turnos con `asyncio.Lock` y arranca un warm-up no bloqueante para evitar respuestas solapadas y el arranque lento del primer turno.
- Ventana de usuario y VAD: parámetros de duración derivados de `config.yaml` (`vad_min_speech_ms`, `vad_silence_duration_ms`, `vad_min_utterance_ms`) para asegurar turnos ≥ ~1.8s y evitar cortes por silencios breves; tope de seguridad con `max_record_seconds`.
- ASR estabilizado a español: `WhisperASR.transcribe()` fuerza `language="es"` y `task="transcribe"` (configurable) para frenar la detección errática de idiomas.
- Warm-up de Ollama: ping silencioso al crear el procesador LLM para precargar el modelo sin emitir audio.
- Limpieza menor: logs de entrada de audio bajados a `debug` para reducir ruido en tiempo real; voz TTS por defecto fijada a castellano en `LucyConfig`.

## Prueba rápida
- Requisitos: deps ya instaladas (pipecat, webrtcvad, mimic3, ollama con modelo configurado).
- Comando: `python3 lucy_voice/wakeword/listener.py`
  - Flujo esperado: wake word → VAD (ventana más larga) → ASR en español → LLM (turno único, sin paralelos) → TTS → playback; al finalizar playback se resetea wake word.
  - Ver logs: deberían mostrarse arranque de warm-up Ollama, detección de inicio/fin de usuario y un único `TextFrame` por turno.
