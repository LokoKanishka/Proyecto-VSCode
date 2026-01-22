import time
from typing import Generator
from .abstract_engine import AbstractEngine

class MockEngine(AbstractEngine):
    """
    Mock engine that simulates an LLM by streaming hardcoded text.
    """

    def load_model(self, model_name: str) -> bool:
        print(f"[MockEngine] Loading model: {model_name}...")
        time.sleep(0.5)  # Simulate loading delay
        print("[MockEngine] Model loaded successfully.")
        return True

    def generate_response(self, prompt: str, history: list=[]) -> Generator[str, None, None]:
        print(f"[MockEngine] Generating response for: {prompt} (Context: {len(history)} msgs)")
        
        # Hardcoded response to simulate AI
        dummy_response = (
            "Hello! I am a simulated AI running in the Mock Engine.\n\n"
            "Here is a Python code example using Markdown:\n"
            "```python\n"
            "def hello_world():\n"
            "    print('Hello from CodeBlock!')\n"
            "    return True\n"
            "```\n"
            "This ensures that the interface renders code blocks correctly. "
            "Try copying the code above!"
        )

        for char in dummy_response:
            yield char
            time.sleep(0.02)  # Simulate token generation delay (50 tokens/sec)
