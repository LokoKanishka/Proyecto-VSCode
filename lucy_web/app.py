from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import ray
import os
import sys
import base64
import tempfile
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lucy-ray-secret'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10*1024*1024)  # 10MB para audio

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LucyWeb")

# Import consciousness monitor
from lucy_web.consciousness_monitor import start_consciousness_monitor, get_current_consciousness

# Import voice bridge (lazy load para evitar errores si faltan deps)
voice_bridge = None

def get_voice_bridge():
    """Lazy initialization of voice bridge"""
    global voice_bridge
    if voice_bridge is None:
        try:
            from src.engine.voice_bridge import LucyVoiceBridge
            voice_bridge = LucyVoiceBridge()
            log.info("✅ Voice bridge initialized")
        except Exception as e:
            log.warning(f"⚠️ Voice bridge not available: {e}")
            voice_bridge = False  # Mark as unavailable
    return voice_bridge if voice_bridge is not False else None

def get_manager():
    """Connect to Ray and get LucyManager"""
    if not ray.is_initialized():
        try:
            ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
        except Exception:
            # Fallback for local dev if not running
            pass
            
    try:
        return ray.get_actor("LucyManager")
    except ValueError:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    log.info("Client connected")
    manager = get_manager()
    status = "Connected to Ray Cluster" if manager else "Ray Cluster NOT FOUND"
    emit('status', {'message': status, 'type': 'success'})
    
    # Send current consciousness state immediately
    consciousness = get_current_consciousness()
    emit('consciousness_update', consciousness)
    
    # Check voice bridge availability
    vb = get_voice_bridge()
    audio_status = "Voice available" if vb else "Voice unavailable"
    emit('status', {'message': audio_status, 'type': 'info'})

@socketio.on('chat_message')
def handle_chat_message(data):
    user_message = data.get('message', '')
    log.info(f"Received: {user_message}")
    
    emit('message', {'type': 'user', 'content': user_message})
    
    manager = get_manager()
    if not manager:
        emit('error', {'message': 'Lucy Backend (Ray) is not running!'})
        return

    try:
        # Async call to Manager
        future = manager.process_input.remote(user_message)
        response = ray.get(future) # Blocking wait for response
        
        emit('message', {'type': 'assistant', 'content': response})
    except Exception as e:
        log.error(f"Error processing message: {e}")
        emit('message', {'type': 'assistant', 'content': f"Error: {str(e)}"})

@socketio.on('request_consciousness')
def handle_consciousness_request():
    """Client requests current consciousness state"""
    consciousness = get_current_consciousness()
    emit('consciousness_update', consciousness)
    log.debug("Consciousness state sent to client")

@socketio.on('voice_input')
def handle_voice_input(data):
    """
    Procesa audio del browser (WebM/WAV base64)
    Pipeline: audio → transcription → Lucy → TTS → audio back
    """
    try:
        vb = get_voice_bridge()
        if not vb:
            emit('status', {'message': 'Voice bridge not available', 'type': 'error'})
            return
        
        audio_b64 = data.get('audio_b64')
        mime = data.get('mime', 'audio/webm')
        
        if not audio_b64:
            emit('status', {'message': 'No audio data received', 'type': 'error'})
            return
        
        log.info(f"Received voice input ({mime}, {len(audio_b64)} bytes)")
        
        # Decode base64
        audio_bytes = base64.b64decode(audio_b64)
        
        # Save to temp file
        suffix = '.webm' if 'webm' in mime else '.wav'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Convert to WAV 16kHz mono if needed
        wav_path = tmp_path.replace(suffix, '.wav')
        if suffix != '.wav':
            result = subprocess.run([
                'ffmpeg', '-y', '-i', tmp_path,
                '-ar', '16000', '-ac', '1',
                '-f', 'wav', wav_path
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                log.error(f"ffmpeg failed: {result.stderr.decode()}")
                emit('status', {'message': 'Audio conversion failed', 'type': 'error'})
                os.unlink(tmp_path)
                return
        else:
            wav_path = tmp_path
        
        # TODO: Transcribe with voice_bridge
        # (Requiere adaptar voice_bridge para leer de archivo)
        # Por ahora, placeholder:
        text = "[Transcription placeholder - integrate voice_bridge.asr_model]"
        
        emit('transcription', {'text': text})
        emit('status', {'message': f'Transcribed: {text}', 'type': 'info'})
        
        # TODO: Process with Lucy core
        response = f"Entendí: {text}"
        
        # Generate TTS
        vb.say(response)
        
        # Read generated WAV
        response_wav = 'response.wav'
        if os.path.exists(response_wav):
            with open(response_wav, 'rb') as f:
                audio_data = f.read()
            
            # Send back to browser
            audio_b64_out = base64.b64encode(audio_data).decode('utf-8')
            emit('tts_audio', {'audio_b64': audio_b64_out, 'mime': 'audio/wav'})
            log.info("TTS audio sent to client")
        
        # Cleanup
        os.unlink(tmp_path)
        if wav_path != tmp_path:
            os.unlink(wav_path)
        
    except subprocess.TimeoutExpired:
        emit('status', {'message': 'Audio processing timeout', 'type': 'error'})
        log.error("ffmpeg timeout")
    except Exception as e:
        emit('status', {'message': f'Error: {str(e)}', 'type': 'error'})
        log.error(f"Voice input error: {e}", exc_info=True)

# Placeholder for health check
@app.get("/api/health")
def api_health():
    manager = get_manager()
    vb = get_voice_bridge()
    return jsonify({
        "status": "ok" if manager else "partial",
        "ray": bool(manager),
        "voice": bool(vb)
    })

if __name__ == '__main__':
    port = int(os.getenv("LUCY_WEB_PORT", "5000"))
    
    # Start consciousness monitor
    log.info("Starting consciousness monitor...")
    observer = start_consciousness_monitor(socketio)
    
    log.info(f"🚀 Starting Lucy Web on port {port}")
    log.info("✅ Voice bridge integration active")
    log.info("✅ Consciousness monitor active")
    
    try:
        socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
    finally:
        observer.stop()
        observer.join()
        log.info("Consciousness monitor stopped")
