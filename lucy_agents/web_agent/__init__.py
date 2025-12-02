#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lucy Web Agent: búsqueda en la web con DuckDuckGo + Ollama.

Este módulo NO usa smolagents ni litellm. En su lugar:
- Usa duckduckgo_search para obtener noticias/texto.
- Usa ollama.chat con el modelo local configurado (por defecto gpt-oss:20b).
"""

from __future__ import annotations

import os
import textwrap
from typing import Any, Dict, List

import ollama

try:
    from duckduckgo_search import DDGS  # type: ignore
    _HAS_DDGS_CLASS = True
except Exception:
    _HAS_DDGS_CLASS = False
    try:
        from duckduckgo_search import ddg_news  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "No se pudo importar duckduckgo_search. "
            "Instalalo en el entorno .venv-lucy-voz con: "
            "pip install 'duckduckgo-search'"
        ) from exc

DEFAULT_OLLAMA_MODEL_ID: str = os.getenv("LUCY_WEB_AGENT_MODEL", "gpt-oss:20b")


def _search_news(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Busca noticias en DuckDuckGo (modo noticias).

    Devuelve una lista de dicts con claves típicas:
    - title
    - body / snippet
    - url / href / link
    - source
    - date
    """
    if max_results <= 0:
        return []

    if _HAS_DDGS_CLASS:
        from duckduckgo_search import DDGS  # type: ignore

        results: List[Dict[str, Any]] = []
        with DDGS() as ddgs:
            for item in ddgs.news(query, max_results=max_results):
                if not item:
                    continue
                results.append(dict(item))
                if len(results) >= max_results:
                    break
        return results

    # Fallback a API vieja ddg_news
    from duckduckgo_search import ddg_news  # type: ignore

    items = ddg_news(query, max_results=max_results) or []
    return [dict(it) for it in items[:max_results]]


def _build_prompt(task: str, hits: List[Dict[str, Any]]) -> str:
    lines: List[str] = [
        "Tarea de Lucy Web:",
        task.strip(),
        "",
        "A continuación tenés un listado de resultados/noticias obtenidos con DuckDuckGo.",
        "Usá esta información como base factual para responder.",
        "",
    ]
    for idx, h in enumerate(hits, start=1):
        title = str(h.get("title") or "").strip()
        body = str(h.get("body") or h.get("snippet") or "").strip()
        url = str(h.get("url") or h.get("href") or h.get("link") or "").strip()
        source = str(h.get("source") or "").strip()
        date = str(h.get("date") or "").strip()

        snippet = textwrap.shorten(body, width=260, placeholder="…") if body else ""

        lines.append(f"[{idx}] {title}")
        meta_parts = [p for p in (source, date) if p]
        if meta_parts:
            lines.append("    " + " | ".join(meta_parts))
        if snippet:
            lines.append("    " + snippet)
        if url:
            lines.append("    URL: " + url)
        lines.append("")

    lines.append(
        "Instrucciones para Lucy:\n"
        "- Respondé SIEMPRE en español rioplatense, claro y simple.\n"
        "- Explicá el tema como si fuera para estudiantes de secundaria en Argentina.\n"
        "- Podés organizar la respuesta en secciones con subtítulos breves.\n"
        "- Sé honesta con las dudas: si un dato no aparece en las notas, marcálo como incierto."
    )
    return "\n".join(lines)


def run_web_research(
    task: str,
    model_id: str | None = None,
    max_results: int = 8,
) -> str:
    """Ejecuta una búsqueda web y resume usando el modelo local de Ollama.

    Args:
        task: Consigna de usuario, en español, tipo:
            "Buscá noticias recientes sobre la economía argentina y resumilas..."
        model_id: Nombre del modelo de Ollama (ej. "gpt-oss:20b").
                  Si es None, usa DEFAULT_OLLAMA_MODEL_ID.
        max_results: Cantidad de resultados de DuckDuckGo a considerar.

    Returns:
        Un string con la respuesta lista para mostrar/leer.
    """
    task = (task or "").strip()
    if not task:
        raise ValueError("La tarea de búsqueda no puede estar vacía.")

    model_name = model_id or DEFAULT_OLLAMA_MODEL_ID

    hits = _search_news(task, max_results=max_results)
    if not hits:
        return (
            "No pude encontrar resultados en DuckDuckGo para esa búsqueda.\n"
            "Probá reformulando la consigna o usando términos más generales."
        )

    user_prompt = _build_prompt(task, hits)

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "Sos Lucy, un asistente de voz local que usa resultados reales de la web "
                    "para explicar temas de forma clara y crítica. "
                    "No inventes datos concretos si no aparecen en las fuentes."
                ),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    content = response["message"]["content"]
    return content.strip()
