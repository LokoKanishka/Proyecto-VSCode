from loguru import logger
import asyncio
from typing import Optional, List, Dict, Any

from src.engine.ollama_engine import OllamaEngine
from src.engine.semantic_router import SemanticRouter
from src.memory.vector_store import EmbeddedMemory
from src.skills.web_search import WebSearchSkill
from src.skills.youtube_skill import YoutubeSkill
from src.skills.system_control import SystemControlSkill

class LucyOrchestrator:
    def __init__(self, model="dolphin-llama3"):
        logger.info("🎨 Inicializando Orquestador Monolítico de Lucy...")
        
        # 1. Motores de Percepción y Cognición
        self.ollama = OllamaEngine(model=model)
        self.memory = EmbeddedMemory()
        
        # 2. Registro de Habilidades (Skills)
        self._register_skills()
        
        # 3. Estado de la conversación
        self.short_term_memory: List[Dict[str, str]] = []
        self.max_history = 10

    def _register_skills(self):
        """Inicializa y registra todas las habilidades nativas."""
        self.ollama.register_skill(WebSearchSkill())
        self.ollama.register_skill(YoutubeSkill())
        self.ollama.register_skill(SystemControlSkill())

    async def process_input(self, text: str, status_callback=None):
        """
        El flujo principal de pensamiento:
        Recibir -> Recordar -> Razonar -> Actuar -> Responder -> Consolidar
        """
        logger.info(f"📥 Nueva entrada: {text}")
        
        # 1. Recuperar Contexto (RAG)
        context = self.memory.recall(text)
        if context:
            logger.debug(f"🧠 Contexto recuperado: {context[:100]}...")
        
        # 2. Generar Respuesta (incluye Routing y Tool Calling interno)
        full_response = ""
        
        # La respuesta de ollama.generate_response es un generador síncrono
        # Lo envolvemos para el flujo asíncrono del orquestador
        for token in self.ollama.generate_response(text, history=self.short_term_memory, status_callback=status_callback):
            full_response += token
            yield token
            # Pequeña pausa para no bloquear el event loop
            await asyncio.sleep(0)

        # 3. Consolidar Memoria
        if full_response:
            # Guardar en memoria a largo plazo
            self.memory.save_memory(f"Usuario: {text}\nLucy: {full_response}")
            
            # Actualizar memoria a corto plazo
            self.short_term_memory.append({"role": "user", "content": text})
            self.short_term_memory.append({"role": "assistant", "content": full_response})
            
            # Podar historia si es muy larga
            if len(self.short_term_memory) > self.max_history * 2:
                self.short_term_memory = self.short_term_memory[-self.max_history * 2:]

    def reset_context(self):
        """Limpia la memoria de corto plazo."""
        self.short_term_memory = []
        logger.info("🧹 Contexto de conversación reiniciado.")
