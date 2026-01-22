/// LUCY PROJECT STATE - V1.0 STABLE ///
FECHA: Enero 2026
ESTADO: FUNCIONAL

HARDWARE:
- GPU: AMD Radeon RX 580 (No soporta CUDA/ROCm fácil en WSL).
- Entorno: WSL2 (Ubuntu) sobre Windows.

CONFIGURACIÓN CRÍTICA ACTUAL:
1. AUDIO INPUT (Micrófono):
   - Driver: PulseAudio (WSLg).
   - Librería: PyAudio + numpy.
   - Ganancia: DIGITAL_GAIN = 4.0 (x4) en audio_processor.py.
   - Umbral Silencio: 0.50 (VAD en voice_bridge.py).
   - Lógica: Escucha continua en bucle (VoiceBridge unificado con AudioProcessor).

2. AUDIO OUTPUT (Voz):
   - TTS: Mimic3 (Local).
   - Player: aplay/paplay (PulseAudio).
   - Voz: es_ES/m-ailabs_low#karen_savage.

3. IA / CEREBRO:
   - Motor: Ollama (Corriendo localmente).
   - Modelo: tinyllama (Optimizado para CPU).
   - Librería: requests (API HTTP).

4. INTERFAZ (GUI):
   - Librería: CustomTkinter.
   - Tema: Negro (#050505) y Verde Matrix (#00ff41).
   - Fix Importante: No usar 'border_width' en CTkOptionMenu (Crashea la app).

5. ARRANQUE:
   - Se debe usar 'export PYTHONPATH=$(pwd)' antes de ejecutar.
   - Se debe verificar 'pulseaudio --start'.
   - Script de arranque automatizado: ./run_lucy.sh
