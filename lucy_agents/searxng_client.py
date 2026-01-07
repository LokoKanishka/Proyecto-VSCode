from __future__ import annotations

import json
import os
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
    return (os.environ.get("SEARXNG_URL") or os.environ.get("LUCY_SEARXNG_URL") or "http://127.0.0.1:8080").rstrip("/")


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


def _request_json(base_url: str, params: dict[str, str], timeout_sec: float) -> dict[str, Any]:
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
        if getattr(resp, "status", 200) != 200:
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'unknown')}")
    return json.loads(raw.decode("utf-8", errors="replace"))


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
    if not query:
        return [], ["missing query"], _base_url() if base_url is None else base_url.rstrip("/")

    url = _base_url() if base_url is None else base_url.rstrip("/")
    timeout = _env_float("SEARXNG_TIMEOUT_SEC", 10.0) if timeout_sec is None else timeout_sec

    try:
        payload = _request_json(
            url,
            _build_params(query=query, language=language, safesearch=safesearch, time_range=time_range),
            timeout,
        )
    except (HTTPError, URLError, RuntimeError, ValueError) as exc:
        return [], [f"searxng_error: {exc}"], url

    results: List[dict[str, Any]] = []
    for item in payload.get("results", []):
        title = (item.get("title") or "").strip()
        link = (item.get("url") or "").strip()
        snippet = (item.get("content") or item.get("snippet") or "").strip()
        engine = item.get("engine")
        if not engine:
            engines = item.get("engines")
            if isinstance(engines, list) and engines:
                engine = engines[0]
        results.append(
            {
                "title": title,
                "url": link,
                "snippet": snippet,
                "engine": engine,
            }
        )
        if len(results) >= max(0, int(num_results)):
            break

    return results, [], url
