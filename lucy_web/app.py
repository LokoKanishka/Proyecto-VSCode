from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import asyncio
import json
from threading import Thread
import sys
import os
import base64
import io
import subprocess
import wave
import shutil

# Add parent directory to path to import lucy_voice
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.voice_pipeline import LucyOrchestrator
import numpy as np
import time
try:
    import soundfile as sf
except Exception as exc:  # pragma: no cover - dependency guard
    sf = None
    logging.getLogger("LucyWeb").warning("soundfile no disponible: %s", exc)

FFMPEG_BIN = shutil.which("ffmpeg")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lucy-voice-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LucyWeb")

# Global orchestrator instance
orchestrator = None
config = None

def init_lucy():
    """Initialize Lucy Voice components"""
    global orchestrator, config
    
    config_path = "config.yaml"
    if os.path.exists(config_path):
        config = LucyConfig.load_from_yaml(config_path)
        log.info(f"Config loaded from {config_path}")
    else:
        config = LucyConfig()
        log.info("Using default config")
    
    orchestrator = LucyOrchestrator(config)
    log.info("Lucy Orchestrator initialized")


def _decode_audio_b64(audio_b64: str, target_sr: int) -> np.ndarray:
    """Decode base64 audio (webm/ogg/pcm) to mono float32 at target_sr."""
    raw = base64.b64decode(audio_b64)

    # 1) Try soundfile if available and format is supported
    if sf is not None:
        try:
            data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
            data = data[:, 0] if data.ndim > 1 else data.reshape(-1)
            if sr != target_sr and sr > 0:
                duration = len(data) / sr
                target_len = int(duration * target_sr)
                if target_len > 0:
                    data = np.interp(
                        np.linspace(0, len(data), target_len, endpoint=False),
                        np.arange(len(data)),
                        data,
                    ).astype("float32")
            return data
        except Exception:
            pass

    # 2) Fallback to ffmpeg (webm/opus, etc.)
    if FFMPEG_BIN:
        try:
            proc = subprocess.run(
                [
                    FFMPEG_BIN,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    "pipe:0",
                    "-ar",
                    str(target_sr),
                    "-ac",
                    "1",
                    "-f",
                    "f32le",
                    "pipe:1",
                ],
                input=raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            audio_bytes = proc.stdout
            data = np.frombuffer(audio_bytes, dtype=np.float32)
            return data
        except Exception as exc:
            log.error(f"ffmpeg decode failed: {exc}")
            return np.array([], dtype="float32")
    log.error("No hay backend de audio para decodificar (soundfile y ffmpeg ausentes).")
    return np.array([], dtype="float32")


def _tts_to_wav_b64(text: str, orchestrator: LucyOrchestrator) -> str:
    """
    Ejecuta TTS y devuelve un WAV en base64 (16-bit PCM) para reproducir en el navegador.
    """
    if not text or orchestrator is None or getattr(orchestrator, "tts", None) is None:
        return ""
    try:
        audio_data, sr = orchestrator.tts.synthesize(text)
        if audio_data is None or sr is None:
            return ""
        # Convertir a int16 PCM
        pcm16 = np.clip(audio_data, -1.0, 1.0)
        pcm16 = (pcm16 * 32767).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(sr))
            wf.writeframes(pcm16.tobytes())
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        log.warning(f"TTS synth failed: {exc}")
        return ""

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')

@app.route('/api/models')
def get_models():
    """Get available Ollama models"""
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        models = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                parts = line.split()
                if parts:
                    models.append(parts[0])
        return jsonify({'models': models})
    except Exception as e:
        log.error(f"Error getting models: {e}")
        return jsonify({'models': [], 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    log.info("Client connected")
    backend = "soundfile" if sf is not None else ("ffmpeg" if FFMPEG_BIN else "none")
    emit('status', {'message': f'Connected to Lucy Voice (audio backend: {backend})'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    log.info("Client disconnected")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming chat message"""
    user_message = data.get('message', '')
    log.info(f"Received message: {user_message}")
    
    # Echo user message
    emit('message', {
        'type': 'user',
        'content': user_message
    })
    
    # Get Lucy's response
    try:
        response = orchestrator.llm.generate_response(user_message)

        # Send Lucy's response
        emit('message', {
            'type': 'assistant',
            'content': response
        })

        # Send TTS audio to client (optional playback)
        tts_b64 = _tts_to_wav_b64(response, orchestrator)
        if tts_b64:
            emit('tts_audio', {
                'audio_b64': tts_b64,
                'mime': 'audio/wav'
            })

    except Exception as e:
        log.error(f"Error generating response: {e}")
        emit('error', {'message': str(e)})

@socketio.on('voice_input')
def handle_voice_input(data):
    """Handle voice input (audio data)"""
    log.info("Received voice input")

    if orchestrator is None:
        emit('error', {'message': 'Orchestrator not initialized'})
        return
    if sf is None and not FFMPEG_BIN:
        emit('error', {'message': 'Audio backend missing (install soundfile or ffmpeg)'})
        return

    start_time = time.time()
    metrics = {}
    try:
        audio_b64 = data.get('audio_b64')
        if not audio_b64:
            emit('error', {'message': 'No audio received'})
            return

        audio = _decode_audio_b64(audio_b64, target_sr=orchestrator.config.sample_rate)
        if audio.size == 0:
            emit('status', {'message': 'No speech detected'})
            return

        metrics['audio_samples'] = int(audio.size)
        metrics['audio_duration_s'] = float(audio.size) / max(orchestrator.config.sample_rate, 1)

        # 1) ASR
        asr_start = time.time()
        text, lang = orchestrator.asr.transcribe(audio)
        asr_end = time.time()
        metrics['asr_ms'] = int((asr_end - asr_start) * 1000)
        if not text.strip():
            emit('status', {'message': 'No speech detected'})
            return

        emit('message', {'type': 'user', 'content': text})

        # 2) LLM
        llm_start = time.time()
        reply = orchestrator.llm.generate_response(text)
        llm_end = time.time()
        metrics['llm_ms'] = int((llm_end - llm_start) * 1000)
        emit('message', {'type': 'assistant', 'content': reply})

        # 3) Opcional: audio al navegador
        tts_b64 = _tts_to_wav_b64(reply, orchestrator)
        if tts_b64:
            emit('tts_audio', {'audio_b64': tts_b64, 'mime': 'audio/wav'})

        # 4) Server-side playback (local speakers)
        try:
            orchestrator.speak(reply)
        except Exception as speak_exc:
            log.warning(f"No se pudo reproducir audio: {speak_exc}")

        metrics['total_ms'] = int((time.time() - start_time) * 1000)
        emit('status', {'message': 'Voice turn completed', 'metrics': metrics})

    except Exception as e:
        log.error(f"Error processing voice: {e}")
        emit('error', {'message': str(e)})

@socketio.on('update_config')
def handle_update_config(data):
    """Update Lucy configuration"""
    global config
    
    try:
        if 'ollama_model' in data:
            config.ollama_model = data['ollama_model']
            orchestrator.llm.model_name = data['ollama_model']
            log.info(f"Model changed to: {data['ollama_model']}")
        
        emit('status', {'message': 'Configuration updated'})
        
    except Exception as e:
        log.error(f"Error updating config: {e}")
        emit('error', {'message': str(e)})

@app.get("/api/health")
def api_health():
    """Simple health/status for web UI."""
    backend = "soundfile" if sf is not None else ("ffmpeg" if FFMPEG_BIN else "none")
    return jsonify({
        "status": "ok" if orchestrator else "not_initialized",
        "audio_backend": backend,
        "model": getattr(orchestrator.llm, "model_name", None) if orchestrator else None,
    })

if __name__ == '__main__':
    log.info("Starting Lucy Voice Web UI...")
    init_lucy()
    host = os.getenv("LUCY_WEB_HOST", "0.0.0.0")
    try:
        port = int(os.getenv("LUCY_WEB_PORT", "5000"))
    except ValueError:
        port = 5000
    log.info("Server starting on http://%s:%d", host, port)
    debug_mode = os.getenv("FLASK_DEBUG", "1") != "0"
    allow_unsafe = os.getenv("LUCY_WEB_ALLOW_UNSAFE", "0") == "1"
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug_mode,
        allow_unsafe_werkzeug=allow_unsafe,
    )
