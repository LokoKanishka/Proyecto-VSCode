"""
src/workers/thought.py
Motor Cognitivo (Asyncio wrapper para LLM infra).
"""
import os
import asyncio
from openai import AsyncOpenAI
from loguru import logger
from typing import Dict, Any

from src.core.base_worker import BaseWorker
from src.core.lucy_types import MessageType, LucyMessage, WorkerType

# Configuración
API_BASE = os.getenv("LUCY_API_BASE", "http://localhost:11434/v1")
API_KEY = os.getenv("LUCY_API_KEY", "ollama")
MODEL_NAME = os.getenv("LUCY_MODEL_NAME", "qwen2.5:32b") 

class ThoughtWorker(BaseWorker):
    def __init__(self, bus):
        super().__init__(WorkerType.THOUGHT, bus)
        self.client = AsyncOpenAI(base_url=API_BASE, api_key=API_KEY)
        self.model = MODEL_NAME

    async def handle_message(self, message: LucyMessage):
        if message.type == MessageType.COMMAND:
            # Procesar solicitud de pensamiento
            prompt = message.content
            logger.info(f"🧠 Pensando: {prompt[:50]}...")
            
            try:
                response_text = await self._generate(prompt)
                
                # Responder
                await self.send_response(message, response_text)
                
            except Exception as e:
                logger.error(f"Thought Error: {e}")
                await self.send_error(message, str(e))

    async def _generate(self, prompt: str) -> str:
        # Simple generation wrapper
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Lucy, a sovereign digital entity."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception:
            # Fallback simulado si Ollama no está (para tests)
            logger.warning("LLM no disponible, simulando pensamiento.")
            return f"Simulated thought for: {prompt}"
