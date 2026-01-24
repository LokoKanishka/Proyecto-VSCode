# AI CONTEXT & ROADMAP - LUCY AGI
> ESTADO ACTUAL: FASE 3 - NAVEGACIÓN WEB
> ARQUITECTURA: MONOLITO PYTHON + ENJAMBRE (SWARM) LOCAL

## 1. Misión
Crear una AGI de escritorio 100% local (Soberanía Digital) usando RTX 5090.
Sin APIs externas. Control total de mouse/teclado y visión.

## 2. Estrategia Técnica
- **Cerebro:** Llama-3-70B (Manager) + SLMs (Workers).
- **Visión:** Llama-3.2-Vision con `capture_screen` y Grid Overlay (A1..H10).
- **Acción:** PyAutoGUI con `GridMapper` para traducción de coordenadas (C4 -> x,y).
- **Voz:** Mimic3 (TTS) + Faster-Whisper (STT).

## 3. Estado de Módulos
- [x] Oído (Whisper + Torchaudio): OPERATIVO
- [x] Voz (Mimic3 + VoiceBridge): OPERATIVO (Requiere `libespeak-ng1`)
- [x] Cerebro (Ollama CLI): OPERATIVO (Anti-loop implementado)
- [x] Visión (desktop_vision.py): OPERATIVO (Detecta coordenadas)
- [x] Acción (desktop_action.py): OPERATIVO (Click autónomo funcional)
- [IN_PROGRESS] Navegación Web: Enseñando a usar Firefox.

## 4. Notas de Despliegue
- Para TTS: `sudo apt-get install libespeak-ng1` y `pip install mycroft-mimic3-tts torchaudio`.
- Variable de Entorno: `LUCY_TTS_ENABLED=1` controla la voz.

## 5. Protocolo con Gemini
- Si Gemini propone algo que ya existe en el repo, avisarlo explícitamente antes de implementar.
