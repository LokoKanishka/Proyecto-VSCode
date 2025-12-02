"""
Paquete Lucy Web Agent.

Provee:
- DEFAULT_OLLAMA_MODEL_ID: modelo por defecto para Ollama.
- run_web_research(task, model_id=None, max_results=8, verbosity=0): función principal.
"""

from .agent import DEFAULT_OLLAMA_MODEL_ID, run_web_research

__all__ = ["DEFAULT_OLLAMA_MODEL_ID", "run_web_research"]
