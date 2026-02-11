"""
Web agent package.

Mantener imports livianos: dependencias opcionales (p.ej. ddgs) se cargan
solo cuando se acceden explícitamente los símbolos públicos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["DEFAULT_OLLAMA_MODEL_ID", "run_web_research"]

if TYPE_CHECKING:
    from .agent import DEFAULT_OLLAMA_MODEL_ID, run_web_research  # noqa: F401


def __getattr__(name: str) -> Any:
    if name == "DEFAULT_OLLAMA_MODEL_ID":
        from .agent import DEFAULT_OLLAMA_MODEL_ID

        return DEFAULT_OLLAMA_MODEL_ID
    if name == "run_web_research":
        from .agent import run_web_research

        return run_web_research
    raise AttributeError(name)
