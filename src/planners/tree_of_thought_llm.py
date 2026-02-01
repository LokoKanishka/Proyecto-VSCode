import json
import logging
import uuid
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import requests

from src.core.types import WorkerType
from src.planners.tree_of_thought import PlanStep

logger = logging.getLogger(__name__)


@dataclass
class ThoughtNode:
    id: str
    parent_id: Optional[str]
    depth: int
    score: float
    content: str
    metadata: Dict = field(default_factory=dict)


class TreeOfThoughtLLMPlanner:
    """
    Tree-of-Thought usando LLM para proponer y valorar planes.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        max_depth: int = 2,
        beam_width: int = 3,
        proposals: int = 3,
    ):
        self.host = host
        self.model = model
        self.max_depth = max_depth
        self.beam_width = beam_width
        self.proposals = proposals
        self._last_tree: List[ThoughtNode] = []
        self.backend = os.getenv("LUCY_TOT_LLM_BACKEND", "ollama")
        self.vllm_url = os.getenv("LUCY_VLLM_URL", "http://localhost:8000")
        self.vllm_model = os.getenv("LUCY_VLLM_MODEL", "qwen2.5-32b")

    def plan(self, prompt: str, context: Iterable[str] | None = None) -> List[PlanStep]:
        root_id = str(uuid.uuid4())
        self._last_tree = [
            ThoughtNode(id=root_id, parent_id=None, depth=0, score=0.0, content="ROOT")
        ]
        frontier = [root_id]
        best_plan: List[PlanStep] = []
        best_score = -1.0

        for depth in range(1, self.max_depth + 1):
            next_frontier = []
            for node_id in frontier:
                proposals = self._propose(prompt, context or [])
                scored = self._value(prompt, proposals)
                for item in scored[: self.beam_width]:
                    node = ThoughtNode(
                        id=str(uuid.uuid4()),
                        parent_id=node_id,
                        depth=depth,
                        score=item.get("score", 0.0),
                        content=json.dumps(item.get("plan", [])),
                        metadata={"rationale": item.get("rationale", "")},
                    )
                    self._last_tree.append(node)
                    next_frontier.append(node.id)
                    if node.score > best_score:
                        best_score = node.score
                        best_plan = item.get("plan", [])
            frontier = next_frontier[: self.beam_width]
            if not frontier:
                break

        if not best_plan:
            return [
                PlanStep(
                    action="chat",
                    target=WorkerType.CHAT,
                    args={"text": prompt, "history": list(context or [])},
                    rationale="Fallback ToT-LLM sin plan.",
                )
            ]
        return [_parse_step(step) for step in best_plan]

    def get_last_tree(self) -> List[Dict]:
        return [
            {
                "id": node.id,
                "parent_id": node.parent_id,
                "depth": node.depth,
                "score": node.score,
                "content": node.content,
                "metadata": node.metadata,
            }
            for node in self._last_tree
        ]

    def _propose(self, prompt: str, context: Iterable[str]) -> List[List[Dict]]:
        system = (
            "Sos un planner. Devolvé SOLO JSON: {\"plans\": [[{action,target,args,rationale}]]}.\n"
            f"Generá {self.proposals} planes alternativos."
        )
        try:
            content = self._call_llm(system, prompt, context)
            data = json.loads(_extract_json(content) or "{}")
            return data.get("plans", [])
        except Exception as exc:
            logger.warning("ToT propose falló: %s", exc)
            return []

    def _value(self, prompt: str, plans: List[List[Dict]]) -> List[Dict]:
        scored: List[Dict] = []
        for plan in plans:
            plan_json = json.dumps(plan, ensure_ascii=False)
            system = (
                "Calificá el plan del 0 al 1 (score) y explicá en 1 frase.\n"
                "Devolvé SOLO JSON: {\"score\":0.0,\"rationale\":\"...\"}."
            )
            try:
                content = self._call_llm(system, f"Pedido: {prompt}\nPlan: {plan_json}", [])
                data = json.loads(_extract_json(content) or "{}")
                scored.append(
                    {
                        "score": float(data.get("score", 0.0)),
                        "rationale": data.get("rationale", ""),
                        "plan": plan,
                    }
                )
            except Exception as exc:
                logger.warning("ToT value falló: %s", exc)
        scored.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return scored

    def _call_llm(self, system: str, user: str, context: Iterable[str]) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Contexto:\n{chr(10).join(context)}\n\n{user}"},
        ]
        if self.backend == "vllm":
            payload = {
                "model": self.vllm_model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 512,
            }
            response = requests.post(f"{self.vllm_url}/v1/chat/completions", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        payload = {"model": self.model, "messages": messages, "stream": False}
        response = requests.post(f"{self.host}/api/chat", json=payload, timeout=25)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")


def _extract_json(text: str) -> Optional[str]:
    if not text:
        return None
    if text.strip().startswith("{") or text.strip().startswith("["):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return None


def _parse_step(step: Dict) -> PlanStep:
    action = step.get("action") or "chat"
    target_raw = (step.get("target") or "chat").lower()
    target = WorkerType.CHAT
    for t in WorkerType:
        if t.value == target_raw or t.name.lower() == target_raw:
            target = t
            break
    args = step.get("args") if isinstance(step.get("args"), dict) else {}
    return PlanStep(action=action, target=target, args=args, rationale=step.get("rationale"))
