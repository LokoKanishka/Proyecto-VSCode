import sys
import traceback

print("Checking imports...")
try:
    from src.engine.swarm_manager import SwarmManager
    print("OK: SwarmManager")
    from src.engine.thought_engine import Planner, ThoughtEngine, ThoughtNode
    print("OK: ThoughtEngine")
    from src.engine.ollama_engine import OllamaEngine
    print("OK: OllamaEngine")
    print("Instantiating OllamaEngine...")
    engine = OllamaEngine(model="qwen2.5:32b")
    print("OK: Instance created")
except Exception:
    traceback.print_exc()
