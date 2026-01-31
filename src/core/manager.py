import logging
import uuid

from src.core.base_worker import BaseWorker
from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType, WorkerType, MemoryEntry
from src.memory.memory_manager import MemoryManager
from src.planners.tree_of_thought import TreeOfThoughtPlanner
from src.resources.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class Manager(BaseWorker):
    """
    El Orquestador Central (Nivel 1) con Memoria RAG.
    Ref: Plan Técnico - Sección 4.2 (Memoria a Largo Plazo)
    """

    def __init__(self, bus: EventBus, memory: MemoryManager):
        super().__init__(WorkerType.MANAGER, bus)
        self.memory = memory
        self.planner = TreeOfThoughtPlanner()
        self.resource_manager = ResourceManager()
        self.bus.subscribe("user_input", self.handle_user_input)
        self.bus.subscribe("broadcast", self.handle_broadcast_event)

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
            if worker_name == WorkerType.BROWSER:
                await self._bridge_browser_response(message)
            if worker_name == WorkerType.VISION:
                await self._handle_vision_to_hands(message)

    async def handle_user_input(self, message: LucyMessage):
        """
        Router Semántico + RAG.
        """
        user_text = message.content
        logger.info("🧠 Manager pensando sobre: '%s'", user_text)

        self.memory.add_message(MemoryEntry(
            role="user",
            content=user_text,
            session_id="current_session"
        ))

        history = self.memory.get_context("current_session", limit=5)
        semantic_fallback = self.memory.semantic_search(user_text, k=3)
        if semantic_fallback:
            await self.send_event(
                "retrieved_memory",
                "Recuperé contexto semántico relevante.",
                {"context": semantic_fallback},
            )
            summary_cmd = LucyMessage(
                sender=self.worker_id,
                receiver=WorkerType.MEMORY,
                type=MessageType.COMMAND,
                content="summarize_history",
                data={
                    "session_id": "current_session",
                    "limit": 10,
                    "reason": "semántica",
                },
            )
            await self.bus.publish(summary_cmd)
        combined_context = [entry["content"] for entry in history]
        combined_context.extend(entry["content"] for entry in semantic_fallback)
        plan = self.planner.plan(user_text, context=combined_context)
        logger.info("🧠 Plan creado con %d pasos", len(plan))

        plan_id = str(uuid.uuid4())
        self.memory.log_plan(
            plan_id,
            user_text,
            [
                {
                    "action": step.action,
                    "target": step.target.value,
                    "args": step.args,
                    "rationale": step.rationale,
                }
                for step in plan
            ],
        )

        for step in plan:
            await self._dispatch_step(step, history)

        if self.memory.count_messages("current_session") >= 40:
            summary_id = self.memory.summarize_history("current_session", limit=20)
            if summary_id:
                await self.send_event(
                    "summary_created",
                    "Generé un resumen automático para mantener el contexto compacto.",
                    {"summary_id": summary_id}
                )

    async def _dispatch_step(self, step, history):
        logger.info(
            "📜 Ejecutando paso: %s hacia %s (%s)",
            step.action,
            step.target.value if isinstance(step.target, WorkerType) else step.target,
            step.rationale or "sin justificación"
        )
        cmd = LucyMessage(
            sender=self.worker_id,
            receiver=step.target,
            type=MessageType.COMMAND,
            content=step.action,
            data={**step.args, "history": history}
        )
        if self.resource_manager.is_gpu_overloaded():
            await self.send_event(
                "final_response",
                "GPU ocupada; priorizo tareas ligeras."
            )
        await self.bus.publish(cmd)

    async def handle_broadcast_event(self, message: LucyMessage):
        if message.type != MessageType.EVENT:
            return
        self.memory.log_event(message.content, message.data or {}, "current_session")
        if message.content == "gpu_pressure":
            usage = message.data.get("usage_pct")
            self.resource_manager.update_gpu_usage(usage)
            logger.warning("⚠️ GPU presión detectada %.2f%%", (usage or 0) * 100)

    async def _bridge_browser_response(self, message: LucyMessage):
        video_url = message.data.get("video_url")
        if not video_url:
            return
        prompt = "Encontrá el botón reproducir para el video que acabo de cargar."
        cmd = LucyMessage(
            sender=self.worker_id,
            receiver=WorkerType.VISION,
            type=MessageType.COMMAND,
            content="analyze_screen",
            data={"prompt": prompt}
        )
        await self.bus.publish(cmd)

    async def _handle_vision_to_hands(self, message: LucyMessage):
        grid_hint = message.data.get("grid_hint")
        if not grid_hint:
            return
        cmd = LucyMessage(
            sender=self.worker_id,
            receiver=WorkerType.HANDS,
            type=MessageType.COMMAND,
            content="click_grid",
            data={"grid_code": grid_hint, "verify": True}
        )
        await self.bus.publish(cmd)

    # Helper functions retained for future heuristics if needed.
