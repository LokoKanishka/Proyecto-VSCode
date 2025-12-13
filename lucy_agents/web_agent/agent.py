from __future__ import annotations

import os
import textwrap
from typing import Dict, List, Optional

from ddgs import DDGS
import ollama
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from .web_search import SearchResult, FetchedPage, build_queries, normalize_query, web_answer

# Nombre del modelo tal como lo ve el servidor de Ollama
DEFAULT_OLLAMA_MODEL_ID = os.getenv("LUCY_WEB_AGENT_OLLAMA_MODEL", "gpt-oss:20b")

DEFAULT_WEB_SEARCH_CONFIG = {
    "provider": "searxng",
    "searxng_url": "http://127.0.0.1:8080",
    "language": "es-AR",
    "safesearch": 1,
    "top_k": 5,
    "fetch_top_n": 3,
    "timeout_s": 12,
}


def load_web_search_config(config_path: str = "config.yaml") -> Dict:
    """
    Carga la sección web_search desde config.yaml si existe.
    """
    if not yaml:
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            return data.get("web_search", {}) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def search_web(query: str, max_results: int = 8) -> List[SearchResult]:
    """
    Usa DDGS (DuckDuckGo) para buscar texto.
    Devuelve una lista de SearchResult.
    """
    results: List[SearchResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=(r.get("title") or "").strip(),
                    snippet=(r.get("body") or "").strip(),
                    url=(r.get("href") or "").strip(),
                    source="ddgs",
                )
            )
    return results


def build_context_from_results(results: List[SearchResult], fetched: List[FetchedPage]) -> str:
    """
    Arma un bloque de texto numerado con los resultados y extractos descargados.
    """
    fetched_by_url = {f.url: f for f in fetched}
    lines: List[str] = []
    for idx, r in enumerate(results, start=1):
        extracted = fetched_by_url.get(r.url)
        extract_text = ""
        if extracted:
            extract_text = textwrap.shorten(extracted.text.replace("\n", " "), width=600, placeholder="...")

        block = textwrap.dedent(
            f"""
            [{idx}] Título: {r.title}
                Resumen: {r.snippet}
                URL: {r.url}
            """
        ).strip()

        if extract_text:
            block = textwrap.dedent(
                f"""
                {block}
                    Extracto: {extract_text}
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
    Hace una búsqueda web con SearXNG (fallback DDGS) y resume usando un modelo local de Ollama.

    task: consigna en español, tal como la formularía la persona usuaria.
    """
    model = model_id or DEFAULT_OLLAMA_MODEL_ID
    cfg = {**DEFAULT_WEB_SEARCH_CONFIG, **load_web_search_config()}

    norm_task = normalize_query(task)
    queries = build_queries(norm_task)
    if verbosity:
        print(f"[Lucy web-agent] Consulta normalizada: {norm_task!r}")
        print(f"[Lucy web-agent] Variantes: {queries}")

    payload = web_answer(
        question=norm_task or task,
        search_fn=search_web,
        provider=cfg.get("provider", "searxng"),
        searxng_url=cfg.get("searxng_url", "http://127.0.0.1:8080"),
        lang=cfg.get("language", "es-AR"),
        safesearch=int(cfg.get("safesearch", 1)),
        top_k=min(max_results, int(cfg.get("top_k", 5))),
        fetch_top_n=int(cfg.get("fetch_top_n", 3)),
        timeout_s=float(cfg.get("timeout_s", 12)),
    )

    results = payload["results"]
    fetched = payload["fetched"]
    used_provider = payload["used_provider"]

    if verbosity:
        print(f"[Lucy web-agent] Usando modelo Ollama: {model}")
        print(
            f"[Lucy web-agent] Proveedor: {used_provider} | resultados brutos: {len(results)} "
            f"| fetch descargados: {len(fetched)}"
        )

    if not results:
        return (
            "No pude encontrar resultados para esa búsqueda.\n"
            "Probá reformulando la consigna o usando términos más generales."
        )

    context = build_context_from_results(results, fetched)

    system_prompt = textwrap.dedent(
        """
        Sos Lucy Web, una asistente de investigación que usa resultados de
        la web para responder preguntas sobre noticias y temas de actualidad.

        Tu tarea es:
        - Leer con atención los resultados provistos.
        - Elaborar una respuesta en castellano claro, como para estudiantes
          de secundaria en Argentina.
        - Mencionar con [n] entre corchetes qué resultado respalda cada
          dato importante (por ejemplo [1], [2], ...).
        - Señalar cuando un dato sea aproximado, incierto o haya desacuerdos
          entre las fuentes.
        - No inventar URLs ni cifras que no aparezcan en los resultados.
        - Al final, listar las fuentes con su URL.
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
    sources_lines = [f"[{idx}] {r.url}" for idx, r in enumerate(results, start=1)]
    if sources_lines:
        answer = f"{answer}\n\nFuentes:\n" + "\n".join(sources_lines)
    return answer
