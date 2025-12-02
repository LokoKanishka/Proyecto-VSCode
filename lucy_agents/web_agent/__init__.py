"""Agente web de Lucy construido con smolagents.

Expone dos funciones principales:

- build_agent(): devuelve un CodeAgent ya configurado.
- run_web_research(task): ejecuta una tarea de investigación web y devuelve el texto final.
"""

from .agent import build_agent, run_web_research

__all__ = ["build_agent", "run_web_research"]
