import asyncio
import time
import sys
import os
import ray
from loguru import logger

# Add project root to path
sys.path.append(os.getcwd())

from src.core.manager import get_or_create_manager, get_or_create_memory, get_or_create_overseer

async def ignite_swarm():
    print("   └── 🟢 [SWARM] Inicializando Enjambre en modo REAL...")
    if not ray.is_initialized():
        ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
    
    # Deploy Core Actors
    manager = get_or_create_manager()
    print("   └── 👑 [CORE] LucyManager Desplegado.")
    
    memory = get_or_create_memory()
    print("   └── 🧠 [MEMORY] Synaptic Cache Conectada.")
    
    overseer = get_or_create_overseer()
    print("   └── 👁️ [OVERSEER] Overseer Vigilando.")
    
    print("   └── 🚀 [SWARM] Motores Listos y Actores Desplegados.")

async def wake_up_lucy():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n" + "="*50)
    print("⚡  LUCY SOVEREIGN KERNEL v1.0 (REAL BOOT)  ⚡")
    print("="*50 + "\n")
    
    start_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Iniciando secuencia de arranque real...\n")

    try:
        await ignite_swarm()
        
        elapsed = time.time() - start_time
        print("\n" + "-"*50)
        print(f"✨  SOBERANÍA ALCANZADA EN: {elapsed:.2f} segundos.")
        print(f"🔥  ENTROPÍA: Mínima.")
        print("-"*50 + "\n")
        print(">> SISTEMA LISTO. ACTORES CORRIENDO EN RAY. ESPERANDO INSTRUCCIÓN.\n")
        
        # Keep process alive to monitor or just exit if actors are detached
        # Since actors are detached, we can exit, but let's keep it running for a bit
        # to ensure stability.
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO DURANTE EL ARRANQUE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(wake_up_lucy())
    except KeyboardInterrupt:
        print("\n\n💤 Hibernando...")

