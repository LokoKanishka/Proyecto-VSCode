"""
LUCY ALEPH THOUGHT - Motor de Inferencia Cognitiva (Qwen 2.5 / OpenAI Compatible).
Ubicación: src/core/thought_actor.py
"""
import ray
import os
import json
import asyncio
from openai import AsyncOpenAI
from loguru import logger
from typing import List, Dict, Any, Optional

# Configuración por defecto (apunta a vLLM u Ollama)
API_BASE = os.getenv("LUCY_API_BASE", "http://localhost:11434/v1")
API_KEY = os.getenv("LUCY_API_KEY", "ollama")
MODEL_NAME = os.getenv("LUCY_MAIN_MODEL", os.getenv("LUCY_VLLM_MODEL", "qwen2.5:32b"))

@ray.remote(num_gpus=0.5, namespace="lucy")
class ThoughtActor:
    def __init__(self):
        self.client = AsyncOpenAI(base_url=API_BASE, api_key=API_KEY)
        self.model = MODEL_NAME
        self.context_window = 16384
        logger.info(f"🧠 THOUGHT ACTOR ONLINE. Model: {self.model} via {API_BASE}")

    async def generate_thought(self, prompt: str, system_prompt: str = "You are Lucy.") -> str:
        """Genera un pensamiento lineal simple."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.2, # Precisión
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return f"ERROR: {str(e)}"

    async def tree_of_thoughts_plan(self, objective: str, depth: int = 3) -> List[Dict]:
        """
        Implementación simplificada de Tree of Thoughts.
        Genera múltiples ramas de razonamiento y selecciona la mejor.
        """
        logger.info(f"🌳 Initiating Tree of Thoughts for: {objective}")
        
        # Paso 1: Generar 3 posibles primeros pasos
        branches = await asyncio.gather(*[
            self.generate_thought(f"Propose step 1 for: {objective}. Option {i+1}", "You are a strategic planner.")
            for i in range(3)
        ])
        
        # Paso 2: Evaluar (simulado por ahora)
        best_thought = branches[0] # Aquí iría el Evaluator
        
        return [{"step": 1, "thought": best_thought, "status": "selected"}]

    async def health_check(self):
        return {"status": "ALIVE", "model": self.model}
