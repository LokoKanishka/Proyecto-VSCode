from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import ray
import os
import sys
import base64
import tempfile
import subprocess
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Dummy logs for tests
BUS_METRICS_LOG = "bus_metrics.jsonl"
BRIDGE_METRICS_LOG = "bridge_metrics.jsonl"
MEMORY_EVENTS_LOG = "memory_retrieval.log"
db_path = "memory.db"

app = Flask(__name__)

app.config['SECRET_KEY'] = 'lucy-ray-secret'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10*1024*1024)  # 10MB para audio

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LucyWeb")

# Import consciousness monitor
from lucy_web.consciousness_monitor import start_consciousness_monitor, get_current_consciousness
from src.core.llm import OllamaClient

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
    if manager:
        status = "Connected to Ray Cluster"
        status_type = "success"
    else:
        status = "Ray Cluster NOT FOUND (Backend offline)"
        status_type = "warning"
    
    emit('status', {'message': status, 'type': status_type})
    
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
    if manager:
        try:
            # Async call to Manager
            future = manager.process_input.remote(user_message)
            response = ray.get(future) # Blocking wait for response
            emit('message', {'type': 'assistant', 'content': response})
            return
        except Exception as e:
            log.error(f"Ray processing error: {e}")
    
    # Fallback to direct Ollama if Ray is missing or failed
    log.info("Using Ollama fallback...")
    try:
        llm = OllamaClient()
        response = llm.chat([
            {"role": "system", "content": "Sos Lucy, una IA asistente. El backend de Ray no está disponible, así que respondés en modo stand-alone."},
            {"role": "user", "content": user_message}
        ])
        
        if "Error connecting" in response:
            emit('message', {'type': 'assistant', 'content': "⚠️ No puedo procesar tu mensaje. El motor de Ray no está activo y Ollama parece estar apagado. Por favor, ejecutá `ollama serve` o iniciá el backend."})
        else:
            emit('message', {'type': 'assistant', 'content': response})
            
    except Exception as e:
        log.error(f"Ollama fallback error: {e}")
        emit('message', {'type': 'assistant', 'content': f"Error crítico: No hay backend disponible (Ray/Ollama)."})

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
        
        # Transcribe with voice_bridge
        text = vb.transcribe_file(wav_path)
        
        if not text:
            emit('status', {'message': 'No speech detected or transcription failed', 'type': 'warning'})
            os.unlink(tmp_path)
            if wav_path != tmp_path:
                os.unlink(wav_path)
            return
        
        emit('transcription', {'text': text})
        emit('status', {'message': f'You said: "{text}"', 'type': 'info'})
        log.info(f"Transcribed: {text}")
        
        # Process with Lucy core (Ray)
        manager = get_manager()
        
        if manager:
            try:
                log.info("Sending to Lucy core...")
                future = manager.process_input.remote(text)
                response = ray.get(future, timeout=30)  # 30s timeout
                log.info(f"Lucy response: {response}")
            except Exception as e:
                log.error(f"Lucy processing error: {e}")
                response = f"Error al procesar tu mensaje: {str(e)}"
        else:
            # Fallback if Ray not available
            log.warning("Ray not available, using fallback response")
            response = f"Entendí tu mensaje: '{text}'. (Lucy core no disponible en este momento)"
        
        # Send text response to chat
        emit('message', {'type': 'assistant', 'content': response})
        
        # Generate TTS
        log.info("Generating TTS...")
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
@app.route('/api/health')
def health():
    """Health check endpoint"""
    manager = get_manager()
    vb = get_voice_bridge()
    
    return jsonify({
        'ok': True,
        'ray': manager is not None,
        'voice': vb is not None,
        'status': 'partial' if manager is None else 'ready'
    })

@app.route('/api/models')
def get_models():
    """Get available models from Ollama or Ray"""
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append(parts[0])  # Solo el nombre
            return jsonify({'models': models})
    except Exception as e:
        log.warning(f"Failed to get Ollama models: {e}")
    
    # Fallback: return default models as strings
    return jsonify({
        'models': ['qwen2.5:32b', 'llama2:7b']
    })

@app.route('/api/stats')
def get_stats():
    """Get system and Ray cluster stats"""
    import psutil
    
    stats = {
        'cpu': {
            'percent': psutil.cpu_percent(interval=0.1),
            'count': psutil.cpu_count()
        },
        'memory': {
            'percent': psutil.virtual_memory().percent,
            'available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
        },
        'ray': {
            'connected': False,
            'nodes': 0
        }
    }
    
    # Try to get Ray stats
    try:
        if ray.is_initialized():
            stats['ray']['connected'] = True
            import ray.util
            cluster_resources = ray.cluster_resources()
            stats['ray']['nodes'] = cluster_resources.get('node:192.168.0.3', cluster_resources.get('node:__internal_head__', 1))
            stats['ray']['gpus'] = int(cluster_resources.get('GPU', 0))
    except Exception as e:
        log.debug(f"Could not get Ray stats: {e}")
    
    return jsonify(stats)

@app.route('/api/bus_metrics')
def get_bus_metrics():
    """Bus metrics for testing"""
    records = []
    if os.path.exists(BUS_METRICS_LOG):
        with open(BUS_METRICS_LOG, 'r') as f:
            for line in f:
                records.append(json.loads(line))
    return jsonify({'summary': {'published': len(records)}, 'records': records})

@app.route('/api/bridge_metrics')
def get_bridge_metrics():
    """Bridge metrics for testing"""
    records = []
    if os.path.exists(BRIDGE_METRICS_LOG):
        with open(BRIDGE_METRICS_LOG, 'r') as f:
            for line in f:
                records.append(json.loads(line))
    return jsonify({'records': records})

@app.route('/api/memory_events')
def get_memory_events():
    """Memory events for testing"""
    events = []
    if os.path.exists(MEMORY_EVENTS_LOG):
        with open(MEMORY_EVENTS_LOG, 'r') as f:
            for line in f:
                events.append({'details': line})
    return jsonify({'events': events})

@app.route('/api/events')
def get_events():
    """Events from DB for testing"""
    import sqlite3
    events = []
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        for row in cursor.fetchall():
            events.append(row)
        conn.close()
    return jsonify({'events': events})

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
