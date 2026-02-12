"""
Consciousness Monitor - Auto-update broadcaster
Monitorea lucy_consciousness.json y pushea cambios a todos los clientes conectados via Socket.IO

Features:
- Watchdog file monitoring
- Broadcast automático vía Socket.IO
- Error handling robusto
- Fallback si archivo no existe
"""

import json
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger


class ConsciousnessWatcher(FileSystemEventHandler):
    """Watches lucy_consciousness.json for changes and broadcasts to clients"""
    
    def __init__(self, socketio, consciousness_file='lucy_consciousness.json'):
        self.socketio = socketio
        self.consciousness_file = consciousness_file
        self.last_data = None
        logger.info(f"👁️ ConsciousnessWatcher initialized - monitoring {consciousness_file}")
    
    def on_modified(self, event):
        """Triggered when consciousness file is modified"""
        if not event.is_directory and event.src_path.endswith(self.consciousness_file):
            self._broadcast_consciousness()
    
    def on_created(self, event):
        """Triggered when consciousness file is created"""
        if not event.is_directory and event.src_path.endswith(self.consciousness_file):
            logger.info("✨ Consciousness file created")
            self._broadcast_consciousness()
    
    def _broadcast_consciousness(self):
        """Read consciousness.json and broadcast to all clients"""
        try:
            with open(self.consciousness_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Evitar spam si datos no cambiaron
            if data != self.last_data:
                self.last_data = data
                self.socketio.emit('consciousness_update', data, broadcast=True)
                logger.debug(f"📡 Consciousness broadcasted: state={data.get('state', 'UNKNOWN')}")
        except FileNotFoundError:
            logger.warning(f"⚠️ Consciousness file not found: {self.consciousness_file}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in consciousness file: {e}")
        except Exception as e:
            logger.error(f"❌ Error broadcasting consciousness: {e}")


def start_consciousness_monitor(socketio, consciousness_file='lucy_consciousness.json'):
    """
    Start monitoring consciousness file
    
    Args:
        socketio: Flask-SocketIO instance
        consciousness_file: Path to consciousness JSON file
    
    Returns:
        Observer instance (keep reference to prevent GC)
    """
    # Ensure file exists (create empty if not)
    if not os.path.exists(consciousness_file):
        logger.warning(f"Creating default consciousness file: {consciousness_file}")
        default_consciousness = {
            "state": "WAITING",
            "entropy": 0.0,
            "activity": 0.0,
            "last_thought": "System initialized",
            "timestamp": "2026-02-11T21:11:00"
        }
        with open(consciousness_file, 'w', encoding='utf-8') as f:
            json.dump(default_consciousness, f, indent=2)
    
    # Create watcher
    event_handler = ConsciousnessWatcher(socketio, consciousness_file)
    
    # Setup observer
    observer = Observer()
    watch_path = os.path.dirname(os.path.abspath(consciousness_file))
    if not watch_path:
        watch_path = '.'
    
    observer.schedule(event_handler, path=watch_path, recursive=False)
    observer.start()
    
    logger.success(f"✅ Consciousness monitor started - watching {watch_path}")
    
    return observer


def get_current_consciousness(consciousness_file='lucy_consciousness.json'):
    """
    Get current consciousness state (for manual requests)
    
    Returns:
        dict: Consciousness data or default offline state
    """
    try:
        with open(consciousness_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Consciousness file not found, returning OFFLINE state")
        return {
            "state": "OFFLINE",
            "entropy": 0.0,
            "activity": 0.0,
            "last_thought": "System offline or not initialized",
            "timestamp": ""
        }
    except Exception as e:
        logger.error(f"Error reading consciousness: {e}")
        return {
            "state": "ERROR",
            "entropy": 1.0,
            "activity": 0.0,
            "last_thought": f"Error: {str(e)}",
            "timestamp": ""
        }
