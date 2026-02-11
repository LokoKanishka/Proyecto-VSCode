from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import ray
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lucy-ray-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LucyWeb")

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
    emit('status', {'message': status})

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

# Placeholder for health check
@app.get("/api/health")
def api_health():
    manager = get_manager()
    return jsonify({"status": "ok" if manager else "error"})

if __name__ == '__main__':
    port = int(os.getenv("LUCY_WEB_PORT", "5000"))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
