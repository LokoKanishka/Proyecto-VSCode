import os
import sys
import threading
import time
from pathlib import Path
import ray
from src.core.manager import get_or_create_manager
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup basic logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

def start_heartbeat():
    def heartbeat_loop():
        heartbeat_file = Path("/tmp/lucy_heartbeat")
        while True:
            heartbeat_file.touch()
            time.sleep(30)
    
    t = threading.Thread(target=heartbeat_loop, daemon=True)
    t.start()
    print("💓 Watchdog heartbeat activo.")

def main() -> None:
    print("\n===========================================")
    print(" 🤖 LUCY AGI - ORCHESTRATOR (RAY MODE)   ")
    print("    (RTX 5090 | Blackwell Architecture)   ")
    print("===========================================")

    start_heartbeat()

    # Initialize Ray
    if not ray.is_initialized():
        print("⚡ Conectando a Ray Cluster...")
        try:
            ray.init(address="auto", namespace="lucy", ignore_reinit_error=True)
            print("✅ Conectado a cluster existente.")
        except Exception:
            print("⚡ Iniciando Ray local (Single Node)...")
            ray.init(namespace="lucy", ignore_reinit_error=True)

    # Get Manager Actor
    print("🧠 Conectando con LucyManager Actor...")
    try:
        manager = get_or_create_manager()
        print("✅ Manager Actor vinculado.")
    except Exception as e:
        print(f"❌ Error vinculando Manager: {e}")
        return

    # Initialize Vision Actor (Background)
    from src.core.manager import get_or_create_vision
    print("👁️ Inicializando Vision Worker (Ray)...")
    get_or_create_vision()

    # Initialize Voice Actor (Background)
    from src.core.manager import get_or_create_voice
    print("🎤 Inicializando Voice Worker (Ray)...")
    voice = get_or_create_voice()
    voice.start.remote()

    # Initialize Planner Actor (Background)
    from src.core.manager import get_or_create_planner
    print("🧠 Inicializando Planner (Brain)...")
    get_or_create_planner()

    # Initialize Action Actor (Background)
    from src.core.manager import get_or_create_action
    print("👋 Inicializando Action Worker (Hand)...")
    get_or_create_action()

    # Initialize Memory Actor (Background)
    from src.core.manager import get_or_create_memory
    print("💾 Inicializando Memory Worker (LanceDB)...")
    get_or_create_memory()

    # Simple CLI Test Loop
    print("✅ Sistema listo. Escribe '/exit' para salir.")
    while True:
        try:
            user_input = input("USER> ")
            if not user_input.strip():
                continue
                
            if user_input.strip().lower() in ["/exit", "exit"]:
                print("👋 Cerrando cliente.")
                break
            
            # Async call to actor
            print("... enviando a Ray ...")
            future = manager.process_input.remote(user_input)
            response = ray.get(future)
            print(f"LUCY> {response}")
            
        except KeyboardInterrupt:
            print("\n👋 Interrupción.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
