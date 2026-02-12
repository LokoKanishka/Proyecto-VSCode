import requests
import json
import os
from loguru import logger

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:32b"):
        self.base_url = base_url
        self.model = os.getenv("LUCY_LLM_MODEL", model)
        logger.info(f"🧠 OllamaClient initialized (Model: {self.model})")

    def generate(self, prompt: str, system: str = None) -> str:
        """Synchronous generation for simplicity in the Actor"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            payload["system"] = system
            
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama Error: {e}")
            return f"Error connecting to brain: {str(e)}"

    def chat(self, messages: list) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Ollama Chat Error: {e}")
            return f"Error connecting to brain: {str(e)}"
