from __future__ import annotations

import os
import textwrap
from typing import Dict, List, Optional

from ddgs import DDGS
import ollama

# Nombre del modelo tal como lo ve el servidor de Ollama
DEFAULT_OLLAMA_MODEL_ID = os.getenv("LUCY_WEB_AGENT_OLLAMA_MODEL", "gpt-oss:20b")


def search_web(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """
    Usa DDGS (DuckDuckGo) para buscar texto.
    Devuelve una lista de dicts con title/snippet/url.
    """
    results: List[Dict[str, str]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": (r.get("title") or "").strip(),
                    "snippet": (r.get("body") or "").strip(),
                    "url": (r.get("href") or "").strip(),
                }
            )
    return results


def build_context_from_results(results: List[Dict[str, str]]) -> str:
    """
    Arma un bloque de texto numerado con los resultados.
    """
    lines: List[str] = []
    for idx, r in enumerate(results, start=1):
        block = textwrap.dedent(
            f"""
            [{idx}] Título: {r["title"]}
                Resumen: {r["snippet"]}
                URL: {r["url"]}
            """
        ).strip()
        lines.append(block)
    return "\n\n".join(lines)


def run_web_research(
    task: str,
    model_id: Optional[str] = None,
    max_results: int = 8,
    verbosity: int = 0,
) -> str:
    """
    Hace una búsqueda web con DDGS y resume usando un modelo local de Ollama.

    task: consigna en español, tal como la formularía la persona usuaria.
    """
    model = model_id or DEFAULT_OLLAMA_MODEL_ID

    if verbosity:
        print(f"[Lucy web-agent] Usando modelo Ollama: {model}")
        print(f"[Lucy web-agent] Buscando en DDGS (max_results={max_results})...")

    results = search_web(task, max_results=max_results)

    if not results:
        return (
            "No pude encontrar resultados en DuckDuckGo para esa búsqueda.\n"
            "Probá reformulando la consigna o usando términos más generales."
        )

    if verbosity:
        print(f"[Lucy web-agent] Se obtuvieron {len(results)} resultados.\n")

    context = build_context_from_results(results)

    system_prompt = textwrap.dedent(
        """
        Sos Lucy Web, una asistente de investigación que usa resultados de
        DuckDuckGo (librería ddgs) para responder preguntas sobre noticias
        y temas de actualidad.

        Tu tarea es:
        - Leer con atención los resultados provistos.
        - Elaborar una respuesta en castellano claro, como para estudiantes
          de secundaria en Argentina.
        - Mencionar con [n] entre corchetes qué resultado respalda cada
          dato importante (por ejemplo [1], [2], ...).
        - Señalar cuando un dato sea aproximado, incierto o haya desacuerdos
          entre las fuentes.
        - No inventar URLs ni cifras que no aparezcan en los resultados.
        """
    ).strip()

    user_content = textwrap.dedent(
        f"""
        Tarea del usuario: {task}

        A continuación tenés un listado de resultados de búsqueda con títulos,
        resúmenes breves y URL. Usalos como base para tu respuesta.

        RESULTADOS:
        {context}
        """
    ).strip()

    if verbosity >= 2:
        print("[Lucy web-agent] Enviando contexto al modelo...\n")

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )

    answer = response["message"]["content"].strip()
    return answer
