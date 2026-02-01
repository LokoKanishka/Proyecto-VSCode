import os

try:
    import ray
    from bs4 import BeautifulSoup
except ImportError:
    ray = None

from prometheus_client import Counter

from src.metrics.prometheus_metrics import DOM_TASKS_COUNTER, RAY_TASKS_IN_FLIGHT

_RAY_ENABLED = ray is not None and os.getenv("LUCY_ENABLE_RAY", "1") in {"1", "true", "yes"}
_DOM_ACTOR = None


if _RAY_ENABLED:
    if not ray.is_initialized():
        ray.init(include_dashboard=False, ignore_reinit_error=True)


    @ray.remote
    class _DomDistillerActor:
        def distill(self, html: str) -> dict:
            """Procesa el HTML y devuelve un DOM simplificado."""
            soup = BeautifulSoup(html, "html.parser")
            headings = []
            for tag in soup.select("h1, h2, h3"):
                text = tag.get_text(" ", strip=True)
                if text:
                    headings.append({"tag": tag.name, "text": text[:120]})
            links = []
            for a in soup.select("a"):
                text = a.get_text(" ", strip=True)
                href = a.get("href", "")
                if text:
                    links.append({"text": text[:160], "href": href})
                if len(links) >= 40:
                    break
            tables = []
            for table in soup.select("table")[:5]:
                rows = []
                for tr in table.select("tr")[:5]:
                    cells = [td.get_text(" ", strip=True)[:80] for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append(rows)
            return {"headings": headings, "links": links, "tables": tables}


def distill_dom_ray(html: str) -> dict:
    """Invoca al actor Ray (si está habilitado) o hace distill en hilo local."""
    if not html:
        return {"headings": [], "links": [], "tables": []}
    DOM_TASKS_COUNTER.inc()
    if not _RAY_ENABLED:
        return _local_distill(html)
    global _DOM_ACTOR
    with RAY_TASKS_IN_FLIGHT.track_inprogress():
        if _DOM_ACTOR is None:
            _DOM_ACTOR = _DomDistillerActor.remote()
        future = _DOM_ACTOR.distill.remote(html)
        try:
            return ray.get(future, timeout=int(os.getenv("LUCY_RAY_DOM_TIMEOUT_S", "10")))
        except Exception as exc:  # pragma: no cover
            return _local_distill(html)


def _local_distill(html: str) -> dict:
    """Distiller alternativo sin Ray (para entornos sin ray instalado)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"headings": [], "links": [], "tables": []}
    soup = BeautifulSoup(html, "html.parser")
    headings = [{"tag": tag.name, "text": tag.get_text(" ", strip=True)[:120]} for tag in soup.select("h1, h2, h3") if tag.get_text(" ")]
    links = []
    for a in soup.select("a")[:40]:
        text = a.get_text(" ", strip=True)
        href = a.get("href", "")
        if text:
            links.append({"text": text[:160], "href": href})
    tables = []
    for table in soup.select("table")[:5]:
        rows = []
        for tr in table.select("tr")[:5]:
            cells = [td.get_text(" ", strip=True)[:80] for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return {"headings": headings, "links": links, "tables": tables}
