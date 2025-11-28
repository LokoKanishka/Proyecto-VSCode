from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import asyncio
import json
from threading import Thread
import sys
import os

# Add parent directory to path to import lucy_voice
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.voice_pipeline import LucyOrchestrator

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
    emit('status', {'message': 'Connected to Lucy Voice'})

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
        
    except Exception as e:
        log.error(f"Error generating response: {e}")
        emit('error', {'message': str(e)})

@socketio.on('voice_input')
def handle_voice_input(data):
    """Handle voice input (audio data)"""
    log.info("Received voice input")
    
    try:
        # Run a voice turn
        result = orchestrator.run_turn(use_vad=True)
        
        if result == "no_speech":
            emit('status', {'message': 'No speech detected'})
        elif result == "stop":
            emit('status', {'message': 'Lucy deactivated'})
        else:
            emit('status', {'message': 'Voice turn completed'})
            
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

if __name__ == '__main__':
    log.info("Starting Lucy Voice Web UI...")
    init_lucy()
    log.info("Server starting on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
