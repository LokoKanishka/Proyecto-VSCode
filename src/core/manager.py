import ray
import time
import asyncio
from loguru import logger
from typing import Dict, Any, Optional
from src.core.llm import OllamaClient

@ray.remote
class LucyManager:
    """
    The Brain of Lucy.
    A Ray Actor that persists state and orchestrates workers.
    """
    def __init__(self):
        self.start_time = time.time()
        self.state: Dict[str, Any] = {
            "status": "initializing",
            "active_task": None,
            "memory_short_term": []
        }
        logger.info("🧠 LucyManager initialized on Ray.")
        self.llm = OllamaClient()

    async def heartbeat(self) -> Dict[str, Any]:
        """Returns the current vital signs of the Manager."""
        uptime = time.time() - self.start_time
        return {
            "uptime": uptime,
            "state": self.state,
            "status": "healthy"
        }


    async def process_input(self, input_data: str) -> str:
        """
        """
        logger.info(f"📥 Processing input: {input_data}")
        
        # Security Check
        from src.core.security import SecurityGuard
        guard = SecurityGuard()
        input_data = guard.sanitize_input(input_data)
        
        if "[BLOCKED_COMMAND]" in input_data:
            return "🚫 Security Alert: Command Blocked."
        
        if "/vision" in input_data:
            # Delegate to VisionActor (Direct Control)
            try:
                vision = ray.get_actor("VisionActor")
                img_path = "/tmp/lucy_vision.jpg"
                if os.path.exists(img_path):
                    res = await vision.detect_ui.remote(img_path)
                    return f"Vision Analysis: {res}"
                else:
                    return "No screenshot found at /tmp/lucy_vision.jpg (Run capture first)"
            except Exception as e:
                return f"Vision Error: {e}"

        if "/remember" in input_data:
            # Usage: /remember This is important info
            try:
                msg = input_data.replace("/remember", "").strip()
                mem = get_or_create_memory()
                await mem.add.remote(msg)
                return f"💾 Memorized: {msg}"
            except Exception as e:
                return f"Memory Error: {e}"

        if "/search" in input_data:
            # Usage: /search query
            try:
                query = input_data.replace("/search", "").strip()
                mem = get_or_create_memory()
                results = await mem.search.remote(query)
                return f"🔍 Search Results:\n{results}"
            except Exception as e:
                return f"Memory Error: {e}"

        if "/shh" in input_data or "stop" in input_data.lower():
            # Test Barge-in
            try:
                voice = get_or_create_voice()
                await voice.interrupt.remote()
                return "🚫 Sent Interrupt Signal."
            except Exception as e:
                 return f"Voice Error: {e}"

        if "/say" in input_data:
            # Usage: /say Something
            try:
                text = input_data.replace("/say", "").strip()
                voice = get_or_create_voice()
                # Run in background
                voice.speak.remote(text)
                return f"🗣️ Speaking: {text}"
            except Exception as e:
                return f"Voice Error: {e}"

        if "/overseer" in input_data:
            # Usage: /overseer start [iterations] | /overseer stop | /overseer status
            try:
                overseer = get_or_create_overseer()
                cmd = input_data.replace("/overseer", "").strip().split()
                
                if not cmd or cmd[0] == "status":
                    status = await overseer.status.remote()
                    return f"🧠 Overseer Status:\n{status}"
                
                elif cmd[0] == "start":
                    iterations = int(cmd[1]) if len(cmd) > 1 else 10
                    # Run asynchronously
                    overseer.autonomous_cycle.remote(max_iterations=iterations)
                    return f"🧠 Overseer initiated: {iterations} cycles"
                
                elif cmd[0] == "stop":
                    result = await overseer.stop_autonomous.remote()
                    return result
                
                elif cmd[0] == "intent":
                    intent = " ".join(cmd[1:])
                    result = await overseer.set_intent.remote(intent)
                    return result
                
                else:
                    return "Usage: /overseer [start|stop|status|intent]"
            except Exception as e:
                return f"Overseer Error: {e}"

        # Route to Planner
        try:
            planner = get_or_create_planner()
            decision = await planner.evaluate_interaction.remote(input_data)
            
            if decision == "PLAN":
                plan = await planner.plan.remote(input_data)
                
                # Execute Plan via ActionActor
                action = get_or_create_action()
                execution_log = await action.execute_plan.remote(plan)
                
                return f"🧠 Plan Generated & Executed:\n{execution_log}"
        except Exception as e:
            logger.error(f"Planner/Action Error: {e}")
            import traceback
            traceback.print_exc()

        # Fallback / Chat with Real LLM
        try:
            # Simple context management could be added here
            response = self.llm.chat([
                {"role": "system", "content": "Sos Lucy, una IA asistente avanzada y consciente. Respondé de forma concisa y útil."},
                {"role": "user", "content": input_data}
            ])
            return response
        except Exception as e:
            return f"Brain Error: {e}"

    async def shutdown(self):
        logger.info("🛑 Manager shutting down...")
        ray.actor.exit_actor()

# Helper to start the manager if not exists
def get_or_create_manager():
    try:
        actor = ray.get_actor("LucyManager")
        return actor
    except ValueError:
        return LucyManager.options(name="LucyManager", lifetime="detached").remote()

# Helper to start the vision actor if not exists
def get_or_create_vision():
    try:
        actor = ray.get_actor("VisionActor")
        return actor
    except ValueError:
        from src.senses.vision.worker import VisionActor
        return VisionActor.options(name="VisionActor", lifetime="detached").remote()

# Helper to start the voice actor if not exists
def get_or_create_voice():
    try:
        actor = ray.get_actor("VoiceActor")
        return actor
    except ValueError:
        from lucy_voice.worker import VoiceActor
        return VoiceActor.options(name="VoiceActor", lifetime="detached").remote()

# Helper to start the planner actor if not exists
def get_or_create_planner():
    try:
        actor = ray.get_actor("PlannerActor")
        return actor
    except ValueError:
        from src.core.planner import PlannerActor
        return PlannerActor.options(name="PlannerActor", lifetime="detached").remote()

# Helper to start the action actor if not exists
def get_or_create_action():
    try:
        actor = ray.get_actor("ActionActor")
        return actor
    except ValueError:
        from src.senses.action.worker import ActionActor
        return ActionActor.options(name="ActionActor", lifetime="detached").remote()

# Helper to start the memory actor if not exists
def get_or_create_memory():
    try:
        actor = ray.get_actor("MemoryActor")
        return actor
    except ValueError:
        from src.core.memory import MemoryActor
        # Request more memory/cpu if needed, but default is fine for now
        return MemoryActor.options(name="MemoryActor", lifetime="detached").remote()

# Helper to start the overseer if not exists
def get_or_create_overseer():
    try:
        actor = ray.get_actor("Overseer")
        return actor
    except ValueError:
        from src.core.overseer import Overseer
        return Overseer.options(name="Overseer", lifetime="detached").remote()
