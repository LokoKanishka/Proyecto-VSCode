from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional

from src.core.types import WorkerType

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    action: str
    target: WorkerType
    args: dict
    rationale: Optional[str] = None


class TreeOfThoughtPlanner:
    """Generador sencillo de planes multi-pasos basado en heurísticas."""

    def plan(self, prompt: str, context: Iterable[str] | None = None) -> List[PlanStep]:
        prompt_lower = prompt.lower()
        plan: List[PlanStep] = []
        wants_vision = self._contains_keywords(prompt_lower, {"pantalla", "mira", "ves", "analiza", "observá", "reflejo"})
        wants_browser = self._contains_keywords(prompt_lower, {"youtube", "navega", "web", "video", "buscar", "goglea", "buscá en"})
        wants_hands = self._contains_keywords(prompt_lower, {"click", "clic", "presiona", "pulsa", "apreta", "botón"})
        wants_typing = self._contains_keywords(prompt_lower, {"escribe", "tipea", "escribí", "anota", "sumá", "pegá"})
        wants_search = self._contains_keywords(prompt_lower, {"busca", "investiga", "encuentra", "search", "qué es", "qué significa"})

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
