import os
import requests
from typing import Dict, List, Optional


class VLLMClient:
    """Cliente simple para API OpenAI-compatible de vLLM."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("LUCY_VLLM_URL", "http://localhost:8000")
        self.model = model or os.getenv("LUCY_VLLM_MODEL", "qwen2.5-32b")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 512) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
