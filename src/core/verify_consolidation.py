import sys
import os

print("🔍 Iniciando Verificación de Consolidación...")

# Verificar lucy_agents
try:
    from lucy_agents.action_router import ACTION_SPECS
    print(f"✅ lucy_agents.action_router cargado correctamente. Acciones: {len(ACTION_SPECS)}")
except ImportError as e:
    print(f"❌ Error cargando lucy_agents.action_router: {e}")
    sys.exit(1)

# Verificar lucy_voice
try:
    from lucy_voice.worker import VoiceActor
    print("✅ lucy_voice.worker (VoiceActor) cargado correctamente.")
except ImportError as e:
    print(f"❌ Error cargando lucy_voice.worker: {e}")
    sys.exit(1)

# Verificar memory fix
try:
    from src.core.memory import MemoryActor
    import time
    print("✅ src.core.memory cargado correctamente.")
except ImportError as e:
    print(f"❌ Error cargando src.core.memory: {e}")
    sys.exit(1)

print("\n🚀 Verificación exitosa. Los nuevos namespaces están activos y funcionales.")
