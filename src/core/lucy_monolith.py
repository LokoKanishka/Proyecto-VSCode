import os
import sys
import time
import threading
import ray
from loguru import logger

# Configurar entorno
os.environ["LUCY_WEB_PORT"] = "5001"
sys.path.append(os.getcwd())

# Importar Core
from src.core.manager import get_or_create_manager, get_or_create_memory, get_or_create_overseer
from lucy_web.app import app, socketio, start_consciousness_monitor

def launch_actors():
    """Despliega los actores en el cluster Ray local"""
    logger.info("🟢 [MONOLITH] Iniciando Ray...")
    # Forzar inicio de nuevo cluster local, ignorando anteriores
    if ray.is_initialized():
        ray.shutdown()
    ray.init(ignore_reinit_error=True, include_dashboard=False)
    
    logger.info("👑 [MONOLITH] Desplegando Actores...")
    manager = get_or_create_manager()
    memory = get_or_create_memory()
    overseer = get_or_create_overseer()
    
    # Esperar a que estén listos
    ray.get(manager.heartbeat.remote())
    logger.info("✅ [MONOLITH] Actores Listos y Conectados.")

def run_web():
    """Inicia el servidor web Flask"""
    logger.info("🚀 [MONOLITH] Iniciando Servidor Web...")
    # Iniciar monitor de consciencia (requiere loop aparte o thread)
    # start_consciousness_monitor(socketio) # Esto ya se llama en app.main, cuidado
    
    # Ejecutar SocketIO
    socketio.run(app, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True, use_reloader=False)

if __name__ == "__main__":
    try:
        # 1. Iniciar Infraestructura + Actores
        launch_actors()
        
        # 2. Iniciar Web (en el main thread para que socketio no se queje)
        # El web server tendrá acceso al Ray cluster porque está en el mismo proceso/contexto
        run_web()
        
    except KeyboardInterrupt:
        logger.info("🛑 [MONOLITH] Apagando...")
        ray.shutdown()
    except Exception as e:
        logger.critical(f"❌ [MONOLITH] Error Fatal: {e}")
        import traceback
        traceback.print_exc()
