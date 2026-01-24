from typing import Any, Dict, List, Optional

from src.skills.base_skill import BaseSkill


class ResearchMemorySkill(BaseSkill):
    def __init__(self, memory: List[str], max_items: int = 50, max_chars: int = 1200):
        self._memory = memory
        self._max_items = max_items
        self._max_chars = max_chars

    @property
    def name(self) -> str:
        return "remember"

    @property
    def description(self) -> str:
        return "Guarda un resumen breve de lo observado para memoria de investigacion."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Resumen breve y concreto de lo observado.",
                }
            },
            "required": ["text"],
        }

    def execute(self, **kwargs) -> str:
        text = kwargs.get("text")
        if text is None:
            return "Error: se requiere text para remember."
        cleaned = str(text).strip()
        if not cleaned:
            return "Error: el texto para remember esta vacio."
        if self._max_chars and len(cleaned) > self._max_chars:
            cleaned = cleaned[: self._max_chars].rstrip() + "..."
        self._memory.append(cleaned)
        if self._max_items and len(self._memory) > self._max_items:
            overflow = len(self._memory) - self._max_items
            if overflow > 0:
                del self._memory[:overflow]
        return f"OK: memoria guardada ({len(self._memory)} items)."
