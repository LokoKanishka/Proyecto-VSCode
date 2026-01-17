from typing import Generator
import ollama
from .abstract_engine import AbstractEngine

class OllamaEngine(AbstractEngine):
    def __init__(self):
        self.model = "phi3" # Default

    def load_model(self, model_name: str) -> bool:
        """
        In Ollama, 'loading' is implicit on chat, but we can verify availability.
        """
        try:
            print(f"[OllamaEngine] Verifying model: {model_name}...")
            # Simple check or 'pull' if needed. For now just set the attribute.
            self.model = model_name
            return True
        except Exception as e:
            print(f"[OllamaEngine] Error loading model: {e}")
            return False

    def list_models(self) -> list[str]:
        """Fetches available models from local Ollama instance."""
        try:
            response = ollama.list()
            # Handle Object-based response (newer library versions)
            if hasattr(response, 'models'):
                return [m.model for m in response.models]
            
            # Handle Dict-based response (older versions/compat)
            if isinstance(response, dict) and 'models' in response:
                return [m.get('name', m.get('model')) for m in response['models']]
                
            return []
        except Exception as e:
            print(f"[OllamaEngine] Error listing models: {e}")
            return []

    def generate_response(self, prompt: str, history: list) -> Generator[str, None, None]:
        """
        Streams response from Ollama using the provided history context.
        """
        # Prepare messages: History + Current Prompt
        messages = history.copy()
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            for chunk in stream:
                content = chunk.get('message', {}).get('content', '')
                if content:
                    yield content
                    
        except Exception as e:
            err_msg = f"[Error: {str(e)}]"
            yield err_msg
