from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import asyncio
import json
import sqlite3
import time
import sys
import os
import base64
import io
import subprocess
import wave
import shutil
from pathlib import Path

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
RESOURCE_LOG = Path("logs/resource_events.jsonl")
BUS_METRICS_LOG = Path("logs/bus_metrics.jsonl")
MEMORY_EVENTS_LOG = Path("logs/memory_retrieval.log")
BRIDGE_METRICS_LOG = Path("logs/bridge_metrics.jsonl")
db_path = Path("lucy_memory.db")

_log_emit_started = False

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


def _load_resource_events(limit: int = 100):
    if not RESOURCE_LOG.exists():
        return []
    with RESOURCE_LOG.open("r", encoding="utf-8") as fd:
        lines = fd.readlines()[-limit:]
    events = []
    for raw in lines:
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return events


def _resource_summary(events):
    gpu = None
    windows = []
    for event in reversed(events):
        if event["event"] == "gpu_pressure" and gpu is None:
            gpu = event["data"].get("usage_pct")
        if event["event"] == "window_opened":
            windows.append(event["data"])
    return {"gpu": gpu, "windows": windows[:5]}


def _tail_jsonl(path: Path, limit: int = 50):
    if not path.exists():
        return []
    lines = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            if raw.strip():
                lines.append(raw.strip())
    return [json.loads(line) for line in lines[-limit:] if line]


def _summarize_bus_metrics(records, last_n: int = 10):
    if not records:
        return {}
    metrics = [rec.get("metrics", {}) for rec in records]
    bridge_records = [rec.get("bridge", {}) for rec in records if rec.get("bridge")]
    latency_records = [rec.get("latency", {}) for rec in records if rec.get("latency")]
    keys = set().union(*(m.keys() for m in metrics))
    summary = {}
    for key in keys:
        values = [m.get(key, 0) for m in metrics if isinstance(m.get(key, 0), (int, float))]
        summary[key] = {
            "latest": values[-1] if values else 0,
            "avg": round(sum(values) / len(values), 2) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
        }
    bridge_summary = {}
    if bridge_records:
        last = bridge_records[-1]
        bridge_summary = {
            "latency_avg_ms": last.get("latency_avg_ms"),
            "latency_p50_ms": last.get("latency_p50_ms"),
            "latency_p95_ms": last.get("latency_p95_ms"),
            "backlog_max": last.get("backlog_max"),
            "dropped": last.get("dropped"),
            "sent": last.get("sent"),
            "received": last.get("received"),
            "url": last.get("url"),
        }
    return {
        "summary": summary,
        "recent": records[-last_n:],
        "bridge": bridge_summary,
        "latency": latency_records[-1] if latency_records else {},
    }


def _load_stage_latency(limit: int = 200):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT details, timestamp FROM events WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
        ("stage_latency", limit),
    )
    rows = cursor.fetchall()
    conn.close()
    events = []
    for details, ts in rows:
        try:
            payload = json.loads(details)
        except Exception:
            payload = {}
        payload["timestamp"] = ts
        events.append(payload)
    return list(reversed(events))


def _summarize_stage_latency(events):
    summary = {}
    for evt in events:
        worker = evt.get("worker") or "unknown"
        action = evt.get("action") or "unknown"
        key = f"{worker}:{action}"
        summary.setdefault(key, []).append(evt.get("elapsed_ms", 0))
    return {
        key: {
            "avg_ms": round(sum(values) / len(values), 2) if values else 0,
            "count": len(values),
        }
        for key, values in summary.items()
    }


def _tail_lines(path: Path, limit: int = 20):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip()]
    return lines[-limit:]


def _ensure_emitters_running():
    global _log_emit_started
    if _log_emit_started:
        return
    _log_emit_started = True
    socketio.start_background_task(_bus_metrics_emitter)
    socketio.start_background_task(_memory_events_emitter)


def _busy_wait_file(path: Path, callback, interval: float):
    pos = 0
    while True:
        try:
            if not path.exists():
                path.parent.mkdir(exist_ok=True, parents=True)
                path.write_text("")
            with path.open("r", encoding="utf-8") as fh:
                fh.seek(pos)
                for line in fh:
                    callback(line.strip())
                pos = fh.tell()
        except OSError:
            pass
        time.sleep(interval)


def _bus_metrics_emitter():
    def handle_line(line: str):
        if not line:
            return
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return
        socketio.emit("bus_metrics_update", {"record": record})

    _busy_wait_file(BUS_METRICS_LOG, handle_line, interval=3.0)


def _memory_events_emitter():
    def handle_line(line: str):
        if not line:
            return
        parts = line.split("|", 2)
        details = parts[-1].strip()
        timestamp = parts[0].strip() if parts else ""
        socketio.emit("memory_event", {"details": details, "timestamp": timestamp})

    _busy_wait_file(MEMORY_EVENTS_LOG, handle_line, interval=4.0)


@app.route('/api/resource_events')
def get_resource_events():
    events = _load_resource_events(limit=200)
    summary = _resource_summary(events)
    return jsonify({"summary": summary, "events": events})


@app.route('/api/plan_log')
def get_plan_log():
    db_path = Path("lucy_memory.db")
    if not db_path.exists():
        return jsonify({"plan": None})
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT prompt, steps, timestamp FROM plan_logs
        ORDER BY timestamp DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"plan": None})
    return jsonify({
        "plan": {
            "prompt": row["prompt"],
            "steps": json.loads(row["steps"]),
            "timestamp": row["timestamp"],
        }
    })


@app.route('/api/bus_metrics')
def get_bus_metrics():
    records = _tail_jsonl(BUS_METRICS_LOG, limit=40)
    summary = _summarize_bus_metrics(records, last_n=10)
    return jsonify({"records": records, "summary": summary})


@app.route('/api/bridge_metrics')
def get_bridge_metrics():
    records = _tail_jsonl(BRIDGE_METRICS_LOG, limit=40)
    return jsonify({"records": records})


@app.route('/api/stage_latency')
def get_stage_latency():
    events = _load_stage_latency(limit=200)
    summary = _summarize_stage_latency(events)
    return jsonify({"summary": summary, "events": events[-20:]})


@app.route('/api/worker_status')
def get_worker_status():
    if not db_path.exists():
        return jsonify({"workers": []})
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT details, timestamp FROM events WHERE type = ? ORDER BY timestamp DESC LIMIT 200",
        ("worker_seen",),
    )
    rows = cursor.fetchall()
    conn.close()
    seen = {}
    for details, ts in rows:
        try:
            payload = json.loads(details) if details else {}
        except Exception:
            payload = {}
        worker = payload.get("worker")
        if worker and worker not in seen:
            seen[worker] = ts
    workers = [{"worker": name, "last_seen": ts} for name, ts in seen.items()]
    return jsonify({"workers": workers})


@app.route('/api/memory_events')
def get_memory_events():
    lines = _tail_lines(MEMORY_EVENTS_LOG, limit=25)
    entries = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) >= 2:
            timestamp = parts[0].strip()
            payload = parts[1].strip() if len(parts) == 2 else parts[2].strip()
            entries.append({"timestamp": timestamp, "details": payload})
        else:
            entries.append({"raw": line})
    return jsonify({"events": entries})


@socketio.on('connect')
def _on_socket_connect():
    _ensure_emitters_running()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT prompt, steps, timestamp FROM plan_logs
        ORDER BY timestamp DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"plan": None})
    return jsonify({
        "plan": {
            "prompt": row["prompt"],
            "timestamp": row["timestamp"],
            "steps": json.loads(row["steps"])
        }
    })


@app.route('/api/memory_summary')
def get_memory_summary():
    db_path = Path("lucy_memory.db")
    if not db_path.exists():
        return jsonify({"summary": None, "note": "base de memoria no encontrada"})
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content, timestamp FROM messages
        WHERE role = 'system' AND content LIKE 'Resumen automático%' 
        ORDER BY timestamp DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"summary": None, "note": "sin resúmenes automáticos aún"})
    return jsonify({"summary": row["content"], "timestamp": row["timestamp"]})


@app.route('/api/watcher_events')
def get_watcher_events():
    db_path = Path("lucy_memory.db")
    if not db_path.exists():
        return jsonify({"events": []})
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT type, details, timestamp FROM events
        ORDER BY timestamp DESC LIMIT 12
    ''')
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        details = {}
        try:
            details = json.loads(row["details"])
        except (TypeError, json.JSONDecodeError):
            pass
        events.append({
            "type": row["type"],
            "timestamp": row["timestamp"],
            "details": details,
        })
    return jsonify({"events": events})


@app.route('/api/events')
def get_events():
    event_type = request.args.get("type")
    if not db_path.exists():
        return jsonify({"events": []})
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if event_type:
        cursor.execute(
            "SELECT type, details, timestamp FROM events WHERE type = ? ORDER BY timestamp DESC LIMIT 50",
            (event_type,),
        )
    else:
        cursor.execute(
            "SELECT type, details, timestamp FROM events ORDER BY timestamp DESC LIMIT 50"
        )
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        details = row["details"]
        try:
            details = json.loads(details)
        except Exception:
            pass
        events.append({
            "type": row["type"],
            "details": details,
            "timestamp": row["timestamp"],
        })
    return jsonify({"events": events})

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
    db_ok = db_path.exists()
    return jsonify({
        "status": "ok" if orchestrator else "not_initialized",
        "audio_backend": backend,
        "model": getattr(orchestrator.llm, "model_name", None) if orchestrator else None,
        "db_ok": db_ok,
        "db_path": str(db_path),
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
