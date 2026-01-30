import logging

from src.core.base_worker import BaseWorker
from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType, WorkerType, MemoryEntry
from src.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class Manager(BaseWorker):
    """
    El Orquestador Central (Nivel 1) con Memoria RAG.
    Ref: Plan Técnico - Sección 4.2 (Memoria a Largo Plazo)
    """

    def __init__(self, bus: EventBus, memory: MemoryManager):
        super().__init__(WorkerType.MANAGER, bus)
        self.memory = memory
        self.bus.subscribe("user_input", self.handle_user_input)

    async def handle_message(self, message: LucyMessage):
        """Maneja respuestas de los workers."""
        if message.type == MessageType.RESPONSE:
            worker_name = message.sender
            content = message.content
            logger.info("🧠 Manager recibió data de %s", worker_name)

            self.memory.add_message(MemoryEntry(
                role="assistant",
                content=f"[{worker_name}] {content}",
                session_id="current_session"
            ))

            await self.send_event("final_response", f"[{worker_name}]: {content}")

    async def handle_user_input(self, message: LucyMessage):
        """
        Router Semántico + RAG.
        """
        user_text = message.content.lower()
        logger.info("🧠 Manager pensando sobre: '%s'", message.content)

        relevant_memories = self.memory.retrieve_relevant(message.content, k=2)
        context_str = ""
        if relevant_memories:
            context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])
            logger.info("💡 Recuerdo desbloqueado: %s...", context_str[:100])

        self.memory.add_message(MemoryEntry(
            role="user",
            content=message.content,
            session_id="current_session"
        ))

        if any(kw in user_text for kw in ["mira", "ves", "pantalla", "analiza"]):
            logger.info("🔀 Derivando a VisionWorker")
            cmd = LucyMessage(
                sender=self.worker_id,
                receiver=WorkerType.VISION,
                type=MessageType.COMMAND,
                content="analyze_screen",
                data={"prompt": message.content}
            )
            await self.bus.publish(cmd)
            return

        if any(kw in user_text for kw in ["busca", "investiga", "encuentra", "search"]):
            logger.info("🔀 Derivando a SearchWorker")
            query = user_text.replace("busca", "").replace("investiga", "").strip()
            cmd = LucyMessage(
                sender=self.worker_id,
                receiver=WorkerType.SEARCH,
                type=MessageType.COMMAND,
                content="search",
                data={"query": query or user_text}
            )
            await self.bus.publish(cmd)
            return

        if any(kw in user_text for kw in ["ejecuta", "codigo", "script", "python"]):
            logger.info("🔀 Derivando a CodeWorker")
            code_snippet = "print('Simulando ejecución de código...')"
            cmd = LucyMessage(
                sender=self.worker_id,
                receiver=WorkerType.CODE,
                type=MessageType.COMMAND,
                content="execute_python",
                data={"code": code_snippet}
            )
            await self.bus.publish(cmd)
            return

        logger.info("🔀 Derivando a ChatWorker")
        history = self.memory.get_context("current_session", limit=5)

        augmented_text = message.content
        if context_str:
            augmented_text = f"CONTEXTO DE MEMORIA (Recuerdos pasados):\n{context_str}\n\nUSUARIO:\n{message.content}"

        cmd = LucyMessage(
            sender=self.worker_id,
            receiver=WorkerType.CHAT,
            type=MessageType.COMMAND,
            content="chat",
            data={
                "text": augmented_text,
                "history": history
            }
        )
        await self.bus.publish(cmd)
