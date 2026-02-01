from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from src.core.types import WorkerType

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    action: str
    target: WorkerType
    args: dict
    rationale: Optional[str] = None
    score: Optional[float] = None
    label: Optional[str] = None

@dataclass
class ThoughtNode:
    """Nodo del árbol de pensamiento."""
    step: Optional[PlanStep] = None
    score: float = 0.0
    depth: int = 0
    parent: Optional["ThoughtNode"] = None
    children: List["ThoughtNode"] = field(default_factory=list)


class TreeOfThoughtPlanner:
    """Generador simple con propuestas + valoración heurística y beam search."""

    def plan(
        self,
        prompt: str,
        context: Iterable[str] | None = None,
        max_depth: int = 2,
        beam_width: int = 3,
    ) -> List[PlanStep]:
        prompt_lower = prompt.lower()
        root = ThoughtNode(step=None, score=0.0, depth=0, parent=None)
        frontier = [root]
        best_leaf = root

        for _depth in range(max_depth):
            next_frontier: List[ThoughtNode] = []
            for node in frontier:
                candidates = self._propose_candidates(prompt, prompt_lower, context or [])
                scored = self._value_candidates(prompt_lower, candidates)
                for step in scored[:beam_width]:
                    child = ThoughtNode(
                        step=step,
                        score=(node.score + (step.score or 0.0)),
                        depth=node.depth + 1,
                        parent=node,
                    )
                    node.children.append(child)
                    next_frontier.append(child)
                    if child.score > best_leaf.score:
                        best_leaf = child
            next_frontier.sort(key=lambda n: n.score, reverse=True)
            frontier = next_frontier[:beam_width]
            if not frontier:
                break

        return self._extract_path(best_leaf)

    def _propose_candidates(
        self,
        prompt: str,
        prompt_lower: str,
        context: Iterable[str],
    ) -> List[PlanStep]:
        plan: List[PlanStep] = []
        url = self._extract_url(prompt)
        wants_vision = self._contains_keywords(prompt_lower, {"pantalla", "mira", "ves", "analiza", "observá", "reflejo"})
        wants_browser = self._contains_keywords(prompt_lower, {"youtube", "navega", "web", "video", "buscar", "goglea", "buscá en"})
        wants_hands = self._contains_keywords(prompt_lower, {"click", "clic", "presiona", "pulsa", "apreta", "botón"})
        wants_typing = self._contains_keywords(prompt_lower, {"escribe", "tipea", "escribí", "anota", "sumá", "pegá"})
        wants_search = self._contains_keywords(prompt_lower, {"busca", "investiga", "encuentra", "search", "qué es", "qué significa"})
        wants_shell = self._contains_keywords(prompt_lower, {"terminal", "comando", "bash", "shell"})
        wants_vscode = self._contains_keywords(prompt_lower, {"vscode", "vs code", "editor"})
        wants_git = self._contains_keywords(prompt_lower, {"git", "commit", "branch", "merge"})
        wants_package = self._contains_keywords(prompt_lower, {"instala", "pip", "dependencia", "paquete"})
        wants_read = self._contains_keywords(prompt_lower, {"leer", "resum", "contenido", "artículo", "pagina", "página"})

        if url and (wants_read or not wants_search):
            plan.append(
                PlanStep(
                    action="distill_url",
                    target=WorkerType.BROWSER,
                    args={"url": url},
                    rationale="Hay una URL explícita; destilo el contenido antes de responder.",
                )
            )
        if wants_vision:
            plan.append(
                PlanStep(
                    action="analyze_screen",
                    target=WorkerType.VISION,
                    args={"prompt": prompt},
                    rationale="La solicitud requiere observar la pantalla."
                )
            )
        if wants_browser and not wants_search:
            plan.append(
                PlanStep(
                    action="search_youtube",
                    target=WorkerType.BROWSER,
                    args={"query": prompt},
                    rationale="Interacción con YouTube o navegación web."
                )
            )
        if wants_search and not wants_browser:
            plan.append(
                PlanStep(
                    action="search",
                    target=WorkerType.SEARCH,
                    args={"query": prompt},
                    rationale="Se requiere investigar información textual."
                )
            )
        if wants_shell:
            plan.append(
                PlanStep(
                    action="run_command",
                    target=WorkerType.SHELL,
                    args={"command": prompt},
                    rationale="Solicitud de comando o terminal."
                )
            )
        if wants_vscode:
            path = self._extract_path(prompt)
            if path:
                plan.append(
                    PlanStep(
                        action="open_file",
                        target=WorkerType.VSCODE,
                        args={"path": path},
                        rationale="Interacción con VS Code."
                    )
                )
        if wants_git:
            plan.append(
                PlanStep(
                    action="status",
                    target=WorkerType.GIT,
                    args={},
                    rationale="Operación Git solicitada."
                )
            )
        if wants_package:
            plan.append(
                PlanStep(
                    action="list",
                    target=WorkerType.PACKAGE,
                    args={},
                    rationale="Gestión de dependencias."
                )
            )
        if wants_hands:
            grid_code = self._extract_grid_code(prompt_lower) or "E5"
            plan.append(
                PlanStep(
                    action="click_grid",
                    target=WorkerType.HANDS,
                    args={"grid_code": grid_code},
                    rationale="La orden indica una acción sobre la pantalla."
                )
            )
        if wants_typing and not wants_hands:
            plan.append(
                PlanStep(
                    action="type_text",
                    target=WorkerType.HANDS,
                    args={"text": prompt},
                    rationale="El usuario pide escribir texto."
                )
            )

        if not plan:
            plan.append(
                PlanStep(
                    action="chat",
                    target=WorkerType.CHAT,
                    args={"text": prompt, "history": list(context)},
                    rationale="No se identificó una intención específica; respondo conversacionalmente."
                )
            )
        return plan

    def _value_candidates(self, prompt_lower: str, candidates: List[PlanStep]) -> List[PlanStep]:
        for step in candidates:
            score = 0.5
            if step.target == WorkerType.VISION and "pantalla" in prompt_lower:
                score += 0.3
            if step.target == WorkerType.SEARCH and "qué" in prompt_lower:
                score += 0.2
            if step.target == WorkerType.BROWSER and "youtube" in prompt_lower:
                score += 0.2
            if step.target == WorkerType.HANDS and any(k in prompt_lower for k in ("click", "clic", "botón")):
                score += 0.2
            if step.target == WorkerType.SHELL and any(k in prompt_lower for k in ("terminal", "comando", "bash")):
                score += 0.2
            if step.target == WorkerType.GIT and "git" in prompt_lower:
                score += 0.2
            if step.target == WorkerType.PACKAGE and any(k in prompt_lower for k in ("pip", "instala", "paquete")):
                score += 0.2
            step.score = score
            if score >= 0.7:
                step.label = "seguro"
            elif score >= 0.55:
                step.label = "maybe"
            else:
                step.label = "imposible"
        return candidates

    @staticmethod
    def _extract_path(node: ThoughtNode) -> List[PlanStep]:
        path: List[PlanStep] = []
        current = node
        while current and current.step is not None:
            path.append(current.step)
            current = current.parent
        return list(reversed(path))

    @staticmethod
    def _contains_keywords(text: str, keywords: set[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _extract_grid_code(text: str) -> Optional[str]:
        import re

        normalized = text.upper()
        pattern = re.compile(r"\b([A-H](?:10|[1-9]))\b")
        match = pattern.search(normalized)
        return match.group(1) if match else None

    @staticmethod
    def _extract_path(text: str) -> Optional[str]:
        import re

        match = re.search(r"(/[^\\s]+)", text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_url(text: str) -> Optional[str]:
        import re

        match = re.search(r"https?://\S+", text or "")
        if not match:
            return None
        return match.group(0).rstrip(").,;")
