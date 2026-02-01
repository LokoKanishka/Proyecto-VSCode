import asyncio
import logging
from typing import Any, Dict, List

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import trafilatura
    HAS_TRAFILA = True
except ImportError:
    HAS_TRAFILA = False

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_EMB = True
except ImportError:
    HAS_EMB = False

try:
    import diskcache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class SearchWorker(BaseWorker):
    """Agente de búsqueda con SearXNG + scraping opcional + ranking semántico."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)
        self.searxng_url = "http://127.0.0.1:8080"
        self.language = "es"
        self.max_retries = 2
        self.retry_base_delay = 0.6
        self._embedder = SentenceTransformer("all-MiniLM-L6-v2") if HAS_EMB else None
        self._cache = diskcache.Cache("data/search_cache") if HAS_CACHE else None

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        command = message.content
        query = (message.data.get("query") or "").strip()
        if message.data.get("searxng_url"):
            self.searxng_url = message.data["searxng_url"]
        if message.data.get("language"):
            self.language = message.data["language"]

        logger.info("🔎 Buscando en la web: '%s'", query)

        if command == "search":
            await self.perform_real_search(message, query, message.data or {})
        else:
            await self.send_error(message, f"Comando desconocido: {command}")

    async def perform_real_search(self, original_msg: LucyMessage, query: str, params: Dict[str, Any]):
        if not query:
            await self.send_error(original_msg, "Necesito una consulta para buscar.")
            return

        max_results = int(params.get("max_results", 8))
        use_scrape = bool(params.get("scrape", True))
        include_snippets = bool(params.get("snippets", True))
        if params.get("max_retries") is not None:
            self.max_retries = int(params.get("max_retries"))

        results: List[Dict[str, Any]] = []
        source = "searxng"

        try:
            if HAS_HTTPX:
                results = await self._with_retries(
                    self._search_searxng,
                    query,
                    max_results=max_results,
                )
            else:
                source = "duckduckgo"
                results = await self._with_retries(
                    self._search_ddg,
                    query,
                    max_results=max_results,
                )
        except Exception as exc:
            logger.warning("Fallo SearXNG, usando DuckDuckGo: %s", exc)
            source = "duckduckgo"
            results = await self._with_retries(
                self._search_ddg,
                query,
                max_results=max_results,
            )

        if not results:
            await self.send_response(original_msg, f"No encontré resultados para '{query}'.")
            return

        if use_scrape and HAS_HTTPX and HAS_TRAFILA:
            results = await self._enrich_with_content(results)

        if self._embedder and results:
            results = self._rank_semantic(query, results)

        formatted_response = f"Encontré {len(results)} resultados ({source}):\n"
        for i, res in enumerate(results[:max_results], 1):
            snippet = res.get("snippet") or ""
            if include_snippets and snippet:
                formatted_response += f"{i}. {res.get('title')}: {snippet[:120]}...\n"
            else:
                formatted_response += f"{i}. {res.get('title')} ({res.get('url')})\n"

        citations = [{"title": r.get("title"), "url": r.get("url")} for r in results[:max_results]]
        await self.send_response(
            original_msg,
            formatted_response,
            {"results": results[:max_results], "source": source, "citations": citations},
        )
        await self.send_event("search_completed", {"query": query, "count": len(results), "source": source})

    async def _with_retries(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.max_retries + 2):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                delay = self.retry_base_delay * attempt
                logger.warning("Reintento %d tras error: %s", attempt, exc)
                await asyncio.sleep(delay)
        if last_exc:
            raise last_exc
        return []

    async def _search_searxng(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        if not HAS_HTTPX:
            return []
        params = {
            "q": query,
            "format": "json",
            "language": self.language,
            "safesearch": 1,
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(f"{self.searxng_url}/search", params=params)
            resp.raise_for_status()
            payload = resp.json()
        results = []
        for item in payload.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content") or item.get("snippet"),
                "score": item.get("score", 0),
            })
        return results

    async def _search_ddg(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        if not HAS_DDG:
            return []

        loop = asyncio.get_running_loop()

        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        raw = await loop.run_in_executor(None, _search)
        results = []
        for item in raw:
            results.append({
                "title": item.get("title"),
                "url": item.get("href") or item.get("url"),
                "snippet": item.get("body", ""),
                "score": item.get("score", 0),
            })
        return results

    async def _enrich_with_content(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for res in results:
                url = res.get("url")
                if not url:
                    continue
                cached = self._cache.get(url) if self._cache else None
                if cached:
                    res.update(cached)
                    continue
                try:
                    response = await self._fetch_with_retries(client, url)
                    if response.status_code >= 400:
                        continue
                    html = response.text
                    text = trafilatura.extract(html) if HAS_TRAFILA else None
                    if text:
                        snippet = text.strip().replace("\n", " ")[:300]
                        res["snippet"] = snippet
                        res["content"] = text[:4000]
                        if self._cache:
                            self._cache.set(url, {"snippet": snippet, "content": text[:4000]}, expire=3600)
                except Exception:
                    continue
        return results

    async def _fetch_with_retries(self, client: "httpx.AsyncClient", url: str):
        last_exc = None
        for attempt in range(1, self.max_retries + 2):
            try:
                return await client.get(url)
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(self.retry_base_delay * attempt)
        raise last_exc

    def _rank_semantic(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._embedder:
            return results
        texts = [f"{r.get('title','')} {r.get('snippet','')}" for r in results]
        query_vec = self._embedder.encode([query], convert_to_numpy=True)[0]
        doc_vecs = self._embedder.encode(texts, convert_to_numpy=True)
        scored = []
        for idx, res in enumerate(results):
            score = float(doc_vecs[idx].dot(query_vec) / ((doc_vecs[idx] ** 2).sum() ** 0.5 + 1e-9))
            res["semantic_score"] = score
            scored.append(res)
        scored.sort(key=lambda r: r.get("semantic_score", 0), reverse=True)
        return scored
