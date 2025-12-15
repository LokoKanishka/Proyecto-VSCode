from __future__ import annotations
import os

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import trafilatura


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "searxng"
    score: float = 0.0


@dataclass
class FetchedPage:
    url: str
    title: str
    text: str
    elapsed_s: float = 0.0


RELIABLE_DOMAINS = [
    "wikipedia.org",
    "argentina.gob.ar",
    "gob.ar",
    "gob.mx",
    "gob.es",
    "un.org",
    "who.int",
    "cdc.gov",
    "nasa.gov",
    "europa.eu",
    "edu.ar",
    ".edu",
    ".ac.",
]


def normalize_query(text: str) -> str:
    """
    Limpia activaciones y muletillas comunes, conservando el español.
    """
    if not text:
        return ""

    lowered = text.strip()
    lowered = re.sub(r"(?i)\\b(lucy|oye lucy|ok lucy|hey lucy)\\b", " ", lowered)

    fillers = [
        "eh",
        "este",
        "emm",
        "mmm",
        "osea",
        "digamos",
        "tipo",
        "bueno",
        "che",
        "a ver",
    ]
    for f in fillers:
        lowered = re.sub(rf"(?i)\\b{re.escape(f)}\\b", " ", lowered)

    # Colapsar repeticiones ("qué es es" -> "qué es")
    lowered = re.sub(r"(?i)\\b(\\w+)(\\s+\\1\\b)+", r"\\1", lowered)

    lowered = re.sub(r"\\s+", " ", lowered)
    return lowered.strip()


def build_queries(q: str) -> List[str]:
    """
    Genera variantes para mejorar recall en SearXNG sin desviar el sentido.

    - Base (tal cual).
    - Si NO es una pregunta definicional, agrega variante '... argentina' (útil para temas locales).
    - Para preguntas definicionales, agrega una keyword que ayude a engines tipo wikipedia/wikidata:
        * si detecta 'número áureo/numero aureo' -> usa 'proporcion aurea' (desambigua contra "golden number"/calendario)
        * si no -> usa versión sin prefijo de pregunta + ASCII sin tildes.
    """
    if not q:
        return []

    q_raw = q.strip()
    qlow = q_raw.lower()

    is_def = bool(re.match(
        r"(?i)^\s*¿?\s*(que|qué)\s+(es|son|significa)\b|^\s*(definici[oó]n|concepto)\s+de\b",
        q_raw
    ))

    queries = [q_raw]

    if (not is_def) and ("argentina" not in qlow):
        queries.append(f"{q_raw} argentina")

    # Variante keyword: saca prefijos típicos de pregunta y artículos iniciales.
    kw = q_raw.lstrip("¿").strip()
    kw = re.sub(r"(?i)^(que|qué)\s+(es|son)\s+", "", kw).strip()
    kw = re.sub(r"(?i)^(que|qué)\s+significa\s+", "", kw).strip()
    kw = re.sub(r"(?i)^definici[oó]n\s+de\s+", "", kw).strip()
    kw = re.sub(r"(?i)^concepto\s+de\s+", "", kw).strip()
    kw = re.sub(r"(?i)^(el|la|los|las|un|una)\s+", "", kw).strip()

    # Desambiguación: "numero aureo" pega mucho en "golden number (time)".
    if is_def and (("número áureo" in qlow) or ("numero aureo" in qlow) or (kw.lower() in ("número áureo","numero aureo","numero áureo"))):
        kw_ascii = "proporcion aurea"
    else:
        import unicodedata
        kw_ascii = "".join(
            c for c in unicodedata.normalize("NFKD", kw)
            if not unicodedata.combining(c)
        )
        kw_ascii = re.sub(r"\s+", " ", kw_ascii).strip()

    lower_set = {x.lower() for x in queries}
    if kw_ascii and kw_ascii.lower() not in lower_set:
        queries.append(kw_ascii)
    elif kw and kw.lower() not in lower_set and len(queries) < 3:
        queries.append(kw)

    # Si todavía no llegamos a 3 y es largo, agregamos una versión corta.
    tokens = q_raw.split()
    if len(queries) < 3 and len(tokens) > 5:
        shortened = " ".join(tokens[:5])
        if shortened.lower() not in {x.lower() for x in queries}:
            queries.append(shortened)

    return queries[:3]


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [(k, v) for k, v in query if not k.lower().startswith("utm_")]
    new_query = "&".join(f"{k}={v}" for k, v in filtered)
    cleaned = parsed._replace(query=new_query, fragment="")
    normalized = urlunsplit(cleaned)
    if normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def dedupe_results(results: Iterable[SearchResult]) -> List[SearchResult]:
    seen = set()
    deduped: List[SearchResult] = []
    for r in results:
        url = canonicalize_url(r.url)
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(SearchResult(**{**r.__dict__, "url": url}))
    return deduped


def _reliability_bonus(url: str) -> float:
    url_lower = url.lower()
    for dom in RELIABLE_DOMAINS:
        if dom in url_lower:
            return 2.5
    return 0.0


def rank_results(results: List[SearchResult], query: str) -> List[SearchResult]:
    terms = [t.lower() for t in query.split() if len(t) > 2]
    ranked: List[SearchResult] = []
    for idx, r in enumerate(results):
        haystack = f"{r.title} {r.snippet}".lower()
        term_score = sum(1.0 for t in terms if t in haystack)
        position_bonus = 1.0 / (1 + idx)
        score = term_score + position_bonus + _reliability_bonus(r.url)
        ranked.append(SearchResult(**{**r.__dict__, "score": score}))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def searx_search(
    queries: Iterable[str],
    base_url: str,
    lang: str = "es-AR",
    safesearch: int = 1,
    timeout_s: float = 12.0,
) -> List[SearchResult]:
    """
    Consulta SearXNG (JSON API) y devuelve resultados combinados de todas las variantes.
    """
    base = base_url.rstrip("/")
    collected: List[SearchResult] = []

    with httpx.Client(
        timeout=timeout_s,
        headers={
            "Accept": "application/json",
            "User-Agent": "Lucy-Web-Agent/1.0 (+local)",
        },
        follow_redirects=True,
    ) as client:
        for q in queries:
            resp = client.post(
                f"{base}/search",
                data={"q": q, "format": "json", "language": lang, "safesearch": safesearch},
            )
            resp.raise_for_status()
            payload = resp.json()

            # LANG_FALLBACK: algunos engines se ponen en CAPTCHA/vacío según región (p.ej. es-AR).
            # Reintentamos con idioma base ('es') y luego sin language antes de usar fallbacks.
            if not payload.get('results'):
                base_lang = ''
                if lang:
                    base_lang = (lang.split('-')[0] if '-' in lang else lang).strip()
                # 1) Retry con idioma base (ej: 'es') si venía 'es-AR'
                if base_lang and base_lang != lang:
                    r2 = client.post(
                        base + '/search',
                        data={'q': q, 'format': 'json', 'language': base_lang, 'safesearch': safesearch},
                    )
                    r2.raise_for_status()
                    p2 = r2.json()
                    if p2.get('results') or p2.get('infoboxes'):
                        payload = p2
                # 2) Retry sin language
                if not payload.get('results'):
                    r3 = client.post(
                        base + '/search',
                        data={'q': q, 'format': 'json', 'safesearch': safesearch},
                    )
                    r3.raise_for_status()
                    p3 = r3.json()
                    if p3.get('results') or p3.get('infoboxes'):
                        payload = p3

            # INFOBOX_FALLBACK: si engines externos bloquean/captcha y 'results' viene vacío,
            # usamos infoboxes (wikidata/wikipedia) como resultados mínimos.
            if not payload.get('results'):
                iboxes = payload.get('infoboxes') or []
                fb = []
                for ib in iboxes:
                    content = (ib.get('content') or '').strip()
                    for u in (ib.get('urls') or []):
                        url = (u.get('url') or '').strip()
                        if not url:
                            continue
                        title = (u.get('title') or ib.get('infobox') or 'infobox').strip()
                        fb.append({'title': title, 'url': url, 'content': content, 'engine': 'infobox'})
                if fb:
                    payload['results'] = fb

            for item in payload.get("results", []):
                collected.append(
                    SearchResult(
                        title=(item.get("title") or "").strip(),
                        url=(item.get("url") or "").strip(),
                        snippet=(item.get("content") or item.get("snippet") or "").strip(),
                        source="searxng",
                    )
                )
    return collected


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
)
def _fetch_url(url: str, timeout_s: float) -> httpx.Response:
    with httpx.Client(
        timeout=timeout_s,
        headers={"User-Agent": "Lucy-Web-Agent/1.0 (+local)"},
        follow_redirects=True,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp


def fetch_and_extract(url: str, timeout_s: float = 12.0, max_chars: int = 6000) -> Optional[FetchedPage]:
    """
    Descarga una página y extrae texto en modo reader (trafilatura).
    """
    start = time.time()
    try:
        resp = _fetch_url(url, timeout_s=timeout_s)
    except Exception:
        return None

    text = trafilatura.extract(resp.text, url=url, include_comments=False, include_links=False)
    if not text:
        return None

    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    elapsed_s = time.time() - start
    title = ""
    return FetchedPage(url=url, title=title, text=text, elapsed_s=elapsed_s)


def web_answer(
    question: str,
    search_fn: Callable[[str, int], List[SearchResult]],
    provider: str = "searxng",
    searxng_url: str = "http://127.0.0.1:8080",
    lang: str = "es-AR",
    safesearch: int = 1,
    top_k: int = 5,
    fetch_top_n: int = 3,
    timeout_s: float = 12.0,
) -> dict:
    """
    Pipeline completo: normaliza, genera queries, busca, deduplica, rankea,
    baja y extrae top páginas, y retorna un payload estructurado.
    """
    norm = normalize_query(question)
    queries = build_queries(norm)
    if not queries:
        queries = [question]

    results: List[SearchResult] = []
    used_provider = provider
    try:
        if provider.lower() == "searxng":
            results = searx_search(queries, base_url=searxng_url, lang=lang, safesearch=safesearch, timeout_s=timeout_s)
    except Exception:
        results = []

    if not results:
        used_provider = "ddgs"
        # Fallback al backend previo.
        primary = queries[0] if queries else norm
        results = search_fn(primary, max_results=top_k)

    results = dedupe_results(results)
    results = rank_results(results, norm or question)[:top_k]

    fetched: List[FetchedPage] = []
    for r in results[:fetch_top_n]:
        page = fetch_and_extract(r.url, timeout_s=timeout_s)
        if page:
            fetched.append(page)

    sources = [{"title": r.title or r.url, "url": r.url, "source": r.source} for r in results]

    return {
        "query": norm or question,
        "used_provider": used_provider,
        "results": results,
        "fetched": fetched,
        "sources": sources,
    }
