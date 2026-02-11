from __future__ import annotations

import json
import os
import time
from typing import Any, List, Optional, Tuple
from urllib import parse, request
from urllib.error import HTTPError, URLError


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _base_url() -> str:
    return (
        os.environ.get("SEARXNG_URL")
        or os.environ.get("LUCY_SEARXNG_URL")
        or "http://127.0.0.1:8080"
    ).rstrip("/")


def _build_params(
    query: str,
    language: str,
    safesearch: int,
    time_range: Optional[str],
) -> dict[str, str]:
    params = {
        "q": query,
        "format": "json",
        "language": language,
        "safesearch": str(safesearch),
    }
    if time_range:
        params["time_range"] = time_range
    return params


def _request_json(
    base_url: str, params: dict[str, str], timeout_sec: float, retry_count: int = 0
) -> dict[str, Any]:
    """Request JSON from SearXNG with retry logic."""
    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            data = parse.urlencode(params).encode("utf-8")
            req = request.Request(
                f"{base_url}/search",
                data=data,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read()
                status = getattr(resp, "status", 200)
                if status != 200:
                    raise RuntimeError(f"HTTP {status}")
            return json.loads(raw.decode("utf-8", errors="replace"))

        except (HTTPError, URLError) as exc:
            last_error = exc
            if attempt < max_retries:
                # Exponential backoff: 0.5s, 1s
                wait_time = 0.5 * (2**attempt)
                time.sleep(wait_time)
                continue
            break
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            break

    # All retries failed
    raise last_error if last_error else RuntimeError("Unknown error in SearXNG request")


def search(
    query: str,
    *,
    num_results: int = 5,
    language: str = "es",
    safesearch: int = 0,
    time_range: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_sec: Optional[float] = None,
) -> Tuple[List[dict[str, Any]], List[str], str]:
    """
    Search using SearXNG with robust error handling.

    Returns:
        (results, errors, base_url_used)
        - results: list of search result dictionaries
        - errors: list of error messages (empty if successful)
        - base_url_used: the SearXNG URL that was queried
    """
    if not query or not query.strip():
        return (
            [],
            ["No se proporcionó una consulta de búsqueda."],
            _base_url() if base_url is None else base_url.rstrip("/"),
        )

    url = _base_url() if base_url is None else base_url.rstrip("/")
    timeout = _env_float("SEARXNG_TIMEOUT_SEC", 10.0) if timeout_sec is None else timeout_sec

    try:
        payload = _request_json(
            url,
            _build_params(
                query=query, language=language, safesearch=safesearch, time_range=time_range
            ),
            timeout,
        )
    except (HTTPError, URLError) as exc:
        error_msg = "No pude conectarme al motor de búsqueda. Verificá la conexión de red o intentá nuevamente."
        return [], [f"searxng_network_error: {error_msg}"], url
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        error_msg = (
            "El motor de búsqueda devolvió una respuesta inválida. Intentá de nuevo más tarde."
        )
        return [], [f"searxng_parse_error: {error_msg}"], url
    except Exception as exc:
        error_msg = "Ocurrió un error inesperado al buscar. Intentá nuevamente."
        return [], [f"searxng_unexpected_error: {exc}"], url

    # Parse results
    raw_results = payload.get("results", [])
    if not raw_results:
        return [], ["No se encontraron resultados para tu búsqueda."], url

    results: List[dict[str, Any]] = []
    for item in raw_results:
        title = (item.get("title") or "").strip()
        link = (item.get("url") or "").strip()
        snippet = (item.get("content") or item.get("snippet") or "").strip()
        engine = item.get("engine")
        if not engine:
            engines = item.get("engines")
            if isinstance(engines, list) and engines:
                engine = engines[0]

        if not link:  # Skip results without URLs
            continue

        results.append(
            {
                "title": title,
                "url": link,
                "snippet": snippet,
                "engine": engine,
            }
        )
        if len(results) >= max(1, int(num_results)):
            break

    if not results:
        return [], ["Los resultados no contenían enlaces válidos."], url

    return results, [], url
