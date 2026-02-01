import logging
import os
import uuid
import re
from typing import List
import time

from src.core.base_worker import BaseWorker
from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType, WorkerType, MemoryEntry
from src.memory.memory_manager import MemoryManager
from src.planners.tree_of_thought import TreeOfThoughtPlanner, PlanStep
from src.resources.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class Manager(BaseWorker):
    """
    El Orquestador Central (Nivel 1) con Memoria RAG.
    Ref: Plan Técnico - Sección 4.2 (Memoria a Largo Plazo)
    """

    def __init__(self, bus: EventBus, memory: MemoryManager, planner=None, swarm=None):
        super().__init__(WorkerType.MANAGER, bus)
        self.memory = memory
        self.planner = planner or TreeOfThoughtPlanner()
        self.resource_manager = ResourceManager()
        self.swarm = swarm
        self.pending_interrupts: List[str] = []
        self._event_last_seen: dict[str, float] = {}
        self._bridge_backpressure_until = 0.0
        self._register_worker_budgets()
        self.bus.subscribe("user_input", self.handle_user_input)
        self.bus.subscribe("broadcast", self.handle_broadcast_event)

    async def handle_message(self, message: LucyMessage):
        """Maneja respuestas de los workers."""
        if message.type == MessageType.RESPONSE:
            worker_name = message.sender
            content = message.content
            logger.info("🧠 Manager recibió data de %s", worker_name)

            self.resource_manager.mark_worker_idle(worker_name)

            self.memory.add_message(MemoryEntry(
                role="assistant",
                content=f"[{worker_name}] {content}",
                session_id="current_session"
            ))

            await self.send_event("final_response", f"[{worker_name}]: {content}")
            if worker_name == WorkerType.BROWSER:
                await self._bridge_browser_response(message)
                await self._maybe_summarize_distilled(message)
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
        plan = self._maybe_add_distill_step(user_text, plan)
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
                    "score": step.score,
                    "label": step.label,
                }
                for step in plan
            ],
        )
        tree_nodes = getattr(self.planner, "get_last_tree", None)
        if callable(tree_nodes):
            try:
                nodes = tree_nodes()
                if nodes:
                    self.memory.log_thought_tree(plan_id, nodes)
            except Exception as exc:
                logger.debug("No pude loguear árbol ToT: %s", exc)

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
        if self.swarm:
            try:
                profile = "vision" if step.target == WorkerType.VISION else "general"
                self.swarm.set_profile(profile)
            except Exception as exc:
                logger.debug("SwarmManager no disponible: %s", exc)
        if self.pending_interrupts:
            interrupt = self.pending_interrupts.pop(0)
            await self.send_event(
                "final_response",
                f"Interrumpí la tarea actual por evento: {interrupt}"
            )
            return
        if isinstance(step.target, WorkerType) and not self.resource_manager.can_schedule(step.target.value):
            await self.send_event(
                "final_response",
                f"Recursos insuficientes para {step.target.value}; pospongo el paso."
            )
            return
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
        if time.time() < self._bridge_backpressure_until and step.target in {
            WorkerType.BROWSER,
            WorkerType.VISION,
        }:
            await self.send_event(
                "final_response",
                "Bridge con presión; pospongo tareas pesadas."
            )
            return
        if isinstance(step.target, WorkerType):
            self.resource_manager.mark_worker_active(step.target.value)
        if self.swarm:
            try:
                self.swarm.swap_for_worker(step.target.value)
            except Exception as exc:
                logger.debug("Swarm swap_for_worker falló: %s", exc)
        await self.bus.publish(cmd)

    async def handle_broadcast_event(self, message: LucyMessage):
        if message.type != MessageType.EVENT:
            return
        throttle_s = float(os.getenv("LUCY_EVENT_THROTTLE_S", "1.0"))
        last_seen = self._event_last_seen.get(message.content)
        now = time.time()
        if last_seen and now - last_seen < throttle_s and message.content in {
            "gpu_usage", "gpu_pressure", "bridge_stats_audit"
        }:
            return
        self._event_last_seen[message.content] = now
        self.memory.log_event(message.content, message.data or {}, "current_session")
        priority = self._event_priority(message.content)
        if priority >= 2:
            self.pending_interrupts.append(message.content)
        if message.content in {"gpu_pressure", "gpu_usage"}:
            usage = message.data.get("usage_pct")
            self.resource_manager.update_gpu_usage(usage)
            if message.content == "gpu_pressure":
                logger.warning("⚠️ GPU presión detectada %.2f%%", (usage or 0) * 100)
            if self.swarm:
                try:
                    self.swarm.auto_manage_vram(usage)
                except Exception as exc:
                    logger.debug("Swarm auto_manage_vram falló: %s", exc)
        if message.content == "bridge_stats_audit":
            self.memory.log_event(
                message.content,
                message.data or {},
                "current_session",
            )
        if message.content == "bridge_backpressure":
            self.memory.log_event(
                message.content,
                message.data or {},
                "current_session",
            )
            self._bridge_backpressure_until = time.time() + 10.0
        if message.content == "browser_action_failed":
            screenshot_b64 = (message.data or {}).get("screenshot_b64")
            if screenshot_b64:
                cmd = LucyMessage(
                    sender=self.worker_id,
                    receiver=WorkerType.VISION,
                    type=MessageType.COMMAND,
                    content="analyze_image",
                    data={
                        "image_b64": screenshot_b64,
                        "prompt": "Detectá el elemento principal para continuar la acción.",
                        "source": "browser_screenshot",
                        "advanced": True,
                    },
                )
                await self.bus.publish(cmd)

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

    async def _maybe_summarize_distilled(self, message: LucyMessage):
        if message.data.get("action") != "distill_url":
            return
        distilled = message.data.get("distilled_text") or ""
        if not distilled:
            return
        prompt = "Resumí el siguiente contenido en 4-6 frases claras y concisas:\n\n" + distilled
        cmd = LucyMessage(
            sender=self.worker_id,
            receiver=WorkerType.CHAT,
            type=MessageType.COMMAND,
            content="chat",
            data={"text": prompt, "history": []},
        )
        await self.bus.publish(cmd)

    async def _handle_vision_to_hands(self, message: LucyMessage):
        grid_hint = message.data.get("grid_hint")
        if message.data.get("source") == "browser_screenshot":
            return
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
    def _register_worker_budgets(self):
        budgets = {
            WorkerType.SEARCH.value: 500,
            WorkerType.CHAT.value: 8000,
            WorkerType.CODE.value: 2000,
            WorkerType.VISION.value: 6000,
            WorkerType.BROWSER.value: 1500,
            WorkerType.HANDS.value: 200,
            WorkerType.MEMORY.value: 500,
            WorkerType.SHELL.value: 200,
            WorkerType.VSCODE.value: 200,
            WorkerType.GIT.value: 100,
            WorkerType.PACKAGE.value: 200,
        }
        for worker_id, mb in budgets.items():
            self.resource_manager.register_worker_budget(worker_id, mb)
    @staticmethod
    def _event_priority(event_name: str) -> int:
        if event_name in {"gpu_pressure", "notification_received", "window_opened"}:
            return 2
        return 0

    def _maybe_add_distill_step(self, user_text: str, plan):
        url = self._extract_url(user_text)
        if not url:
            return plan
        has_browser = any(getattr(step, "target", None) == WorkerType.BROWSER for step in plan)
        has_distill = any(getattr(step, "action", "") == "distill_url" for step in plan)
        wants_read = self._contains_keywords(user_text.lower(), {"leer", "resum", "contenido", "artículo", "pagina", "página"})
        if (wants_read or not has_browser) and not has_distill:
            step = PlanStep(
                action="distill_url",
                target=WorkerType.BROWSER,
                args={"url": url},
                rationale="El usuario dio una URL; destilo el contenido antes de responder.",
            )
            plan = [step, *plan]
        return plan

    @staticmethod
    def _extract_url(text: str) -> str | None:
        match = re.search(r"https?://\S+", text or "")
        if not match:
            return None
        return match.group(0).rstrip(").,;")

    @staticmethod
    def _contains_keywords(text: str, keywords: set[str]) -> bool:
        return any(keyword in text for keyword in keywords)
