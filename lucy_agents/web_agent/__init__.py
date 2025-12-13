"""
Paquete Lucy Web Agent.

Provee:
- DEFAULT_OLLAMA_MODEL_ID: modelo por defecto para Ollama.
- run_web_research(task, model_id=None, max_results=8, verbosity=0): función principal.
  Usa SearXNG local con fallback a DuckDuckGo (ddgs), fetch + extract y cita URLs.
"""

from .agent import DEFAULT_OLLAMA_MODEL_ID, run_web_research

__all__ = ["DEFAULT_OLLAMA_MODEL_ID", "run_web_research"]
