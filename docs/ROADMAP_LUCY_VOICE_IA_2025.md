# Objetivo general
- Mantener una conversación por turnos (wake word → VAD → ASR → LLM → TTS) con latencia estable < 2.5s y sin solapes de respuestas, funcionando 100% local con modelos abiertos.

# Módulos
- Wakeword: `WakeWordNode` con openWakeWord (modelos por defecto), `wakeword_threshold` en `config.yaml`, reset tras playback desde `AudioOutputNode`.
- VAD: `VADNode` (webrtcvad) con ventana de 30 ms, parámetros derivados de `config.yaml` (`vad_min_speech_ms`, `vad_silence_duration_ms`, `vad_min_utterance_ms`, `max_record_seconds`), emite `UserStartedSpeakingFrame`/`UserStoppedSpeakingFrame`.
- ASR: `WhisperASRProcessor` + `WhisperASR` (faster-whisper) forzado a español (`whisper_language="es"`, `whisper_force_language=True`), salida en `TextFrame`.
- LLM: `OllamaLLMProcessor` secuencial con `asyncio.Lock`, warm-up de modelo Ollama en `StartFrame`, soporte básico de tools vía `ToolManager`.
- TTS: `MimicTTSProcessor` (Mimic3), re-muestreo a `sample_rate` si es necesario, playback en `AudioOutputNode`.
- Orquestador: pipeline de Pipecat en `lucy_voice/pipeline/pipecat_graph.py`, arranque con `lucy_voice/wakeword/listener.py`.

# Tareas pendientes
- [ ] Reemplazar wakeword “alexa” por modelo entrenado con “Hola Lucy” y ajustar `wakeword_threshold`/`cooldown` tras validación.
- [ ] Integrar logs estructurados por turno (id_turno, timestamps, texto_ASR, idioma, prompt_LLM, respuesta_LLM, duración TTS) con modo JSON para análisis automático.
- [ ] Implementar backpressure/pausa de captura mientras TTS reproduce para evitar que VAD escuche la propia salida en hardware con cancelación débil.
- [ ] Evaluar ASR en GPU (faster-whisper medium/large) con `compute_type=float16` si hay VRAM suficiente; medir impacto en latencia.
- [ ] Añadir timeout/cancelación de llamadas a Ollama cuando la latencia supere umbral (ej. 6s) y reintentar con modelo más liviano.
- [ ] Integrar front-end alternativo `lucy_talking_llm` (audio-first) como entrada opcional al pipeline Pipecat manteniendo el lock de turnos.
- [ ] Agregar pruebas automáticas de extremo a extremo con WAVs cortos (wake word + frase) que validen secuencialidad de `TextFrame` y ausencia de respuestas dobles.
- [ ] Exponer parámetros de warm-up (prompt y modo silencioso) en config para modelos que requieran preparación distinta.

# Métricas a futuro
- Latencia por turno: {wake word→start_speech, start_speech→ASR, ASR→LLM respuesta, LLM→TTS ready, playback total}.
- Tasa de falsos disparos de wakeword y tasa de activaciones perdidas.
- WER/TER del ASR en español (frases cortas de 2–5s), % de vacíos.
- Ratio de respuestas fuera de turno (respuestas >1 por texto de usuario).
- CPU/GPU utilization y memoria por módulo en sesiones de 5 minutos.

# Consideraciones de hardware
- CPU-only: faster-whisper small/int8 y Mimic3 funcionan pero latencia depende de núcleos; priorizar `beam_size=1` y locks de turnos.
- GPU disponible: preferir modelos whisper medium/large y LLM más livianos (<8B) para mantener tiempo de calentamiento reducido; asegurar VRAM suficiente.
- Audio: dispositivos full-duplex requieren cancelación o pausa de grabación durante playback para evitar eco en VAD/ASR.
