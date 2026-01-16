import json
import re
import subprocess
import unicodedata
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus, urlparse


def _log(msg: str) -> None:
    print(f"[LucyWebAgent] {msg}", flush=True)


KEYWORD_BONUS = (
    "entrevista",
    "programa",
    "capitulo",
    "capítulo",
    "especial",
    "mano a mano",
    "charla",
)
STOPWORDS = {
    "de",
    "del",
    "la",
    "las",
    "lo",
    "los",
    "un",
    "una",
    "en",
    "y",
    "con",
    "para",
    "por",
    "que",
    "el",
    "al",
    "a",
}
# Palabras muy comunes que no aportan mucho a la búsqueda exacta.
# Se usan para separar tokens "fuertes" de tokens genéricos.
COMMON_WORDS = {
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "y",
    "en",
    "con",
    "un",
    "una",
    "programa",
    "entrevista",
    "completo",
    "mano",
    "manos",
    "capitulo",
    "capítulo",
    "charla",
    "especial",
}

ALLOWED_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}


class YouTubeURLResolutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NoYouTubeURLFound(YouTubeURLResolutionError):
    def __init__(self, message: str = "ERROR_NO_URL") -> None:
        super().__init__("ERROR_NO_URL", message)


class BadYouTubeURL(YouTubeURLResolutionError):
    def __init__(self, message: str = "ERROR_BAD_URL") -> None:
        super().__init__("ERROR_BAD_URL", message)


def _is_allowed_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_YT_HOSTS


def _normalize_token(t: str) -> str:
    """
    Normaliza un token para comparación.
    - minúsculas
    - quitar tildes
    - quitar caracteres no alfabéticos al final
    - recortar espacios
    """
    if not t:
        return ""
    norm = unicodedata.normalize("NFD", t.lower())
    norm = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    norm = re.sub(r"[^a-z0-9]+", " ", norm).strip()
    return norm


def _normalize_text(text: str) -> str:
    """Normaliza texto completo quitando tildes y signos raros."""
    return " ".join(_normalize_token(text).split())


def _strong_query_tokens(query: str) -> list[str]:
    """Devuelve tokens relevantes (>=4 chars y no palabras comunes)."""
    tokens: list[str] = []
    normalized = _normalize_text(query)
    for raw in re.split(r"\s+", normalized):
        tok = raw.strip()
        if len(tok) >= 4 and tok not in COMMON_WORDS:
            tokens.append(tok)
    return tokens


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_text(text)
    tokens = set()
    for tok in re.split(r"\s+", normalized):
        if tok and tok not in STOPWORDS:
            tokens.add(tok)
    return tokens


def _score_candidate(entry: Dict[str, Any], strong_tokens: list[str]) -> int:
    """Calcula un puntaje heurístico para un video."""
    title = entry.get("title") or ""
    uploader = entry.get("uploader") or entry.get("channel") or ""

    title_tokens = _tokenize(title)
    channel_tokens = _tokenize(uploader)

    title_matches = {tok for tok in strong_tokens if tok in title_tokens}
    channel_matches = {tok for tok in strong_tokens if tok in channel_tokens}

    if not title_matches and not channel_matches:
        return -1  # descartar candidatos sin coincidencias fuertes

    score = len(title_matches) * 4 + len(channel_matches) * 1

    return score


def _score_entry(entry: Dict[str, Any], channel_hint: Optional[str]) -> int:
    """Calcula un puntaje heurístico para un video."""
    score = 0
    title = (entry.get("title") or "").lower()
    uploader = (entry.get("uploader") or entry.get("channel") or "").lower()

    if channel_hint:
        hint_words = channel_hint.lower().split()
        if all(w in uploader for w in hint_words):
            score += 2
        if any(w in title for w in hint_words):
            score += 1

    if any(kw in title for kw in KEYWORD_BONUS):
        score += 1

    return score


import shutil
try:
    from lucy_agents import searxng_client
except ImportError:
    searxng_client = None

def _search_searxng_fallback(query: str) -> Optional[str]:
    if not searxng_client:
        _log("SearXNG client not available for fallback.")
        return None
    
    searx_query = f"site:youtube.com watch {query}"
    _log(f"Fallback: Searching SearXNG with '{searx_query}'")
    results, errors, _ = searxng_client.search(searx_query, num_results=5)
    
    if errors:
        _log(f"SearXNG errors: {errors}")
    
    for res in results:
        url = res.get("url", "")
        if url and _is_allowed_youtube_url(url):
            _log(f"Fallback: Found URL {url}")
            return url
            
    return None


def _candidate_video_url(entry: Dict[str, Any]) -> Optional[str]:
    if entry.get("webpage_url"):
        return entry.get("webpage_url")
    if entry.get("url"):
        raw = entry.get("url")
        if isinstance(raw, str) and raw.startswith(("http://", "https://")):
            return raw
        if isinstance(raw, str) and not raw.startswith("ytsearch"):
            return f"https://www.youtube.com/watch?v={raw}"
    if entry.get("id"):
        return f"https://www.youtube.com/watch?v={entry.get('id')}"
    return None

def find_youtube_video_url(
    query: str,
    channel_hint: Optional[str] = None,
    strategy: str = "latest",
) -> str:
    """
    Dado un texto de búsqueda y (opcionalmente) un identificador/dica de canal,
    intenta encontrar una URL de video de YouTube que encaje.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        _log("Empty query provided to find_youtube_video_url.")
        raise NoYouTubeURLFound("ERROR_NO_URL: empty query")
        
    # 1. Check yt-dlp availability
    if not shutil.which("yt-dlp"):
         _log("yt-dlp not found. Trying SearXNG fallback.")
         fallback = _search_searxng_fallback(cleaned_query)
         if fallback:
             return fallback
         raise NoYouTubeURLFound("ERROR_NO_URL: yt-dlp missing and no fallback")

    try:
        search_term = cleaned_query
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--flat-playlist",
            f"ytsearch10:{search_term}",
        ]
        _log(f"Running yt-dlp search: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        
        # If yt-dlp fails, fallback immediately
        if proc.returncode != 0:
            _log(f"yt-dlp failed (code {proc.returncode}). Trying SearXNG fallback.")
            fallback = _search_searxng_fallback(cleaned_query)
            if fallback:
                return fallback
            raise NoYouTubeURLFound("ERROR_NO_URL: yt-dlp failed and no fallback")

        stdout = proc.stdout or ""
        if not stdout.strip():
            _log("yt-dlp returned empty output. Trying SearXNG fallback.")
            fallback = _search_searxng_fallback(cleaned_query)
            if fallback:
                return fallback
            raise NoYouTubeURLFound("ERROR_NO_URL: yt-dlp empty output")

        data = json.loads(stdout)
        entries = data.get("entries") or []
        if not entries and isinstance(data, dict) and "webpage_url" in data:
            entries = [data]

        if not entries:
            _log("[LucyWebAgent] No entries from yt-dlp.")
            raise NoYouTubeURLFound("ERROR_NO_URL: no entries")

        strong_tokens = _strong_query_tokens(cleaned_query)
        weak_tokens = [tok for tok in _tokenize(cleaned_query) if tok not in strong_tokens]
        channel_bonus_tokens = _tokenize(channel_hint) if channel_hint else set()

        scored: list[tuple[Dict[str, Any], int, int]] = []
        for e in entries:
            title = e.get("title") or ""
            uploader = e.get("uploader") or e.get("channel") or ""
            candidate_tokens = _tokenize(f"{title} {uploader}")

            name_matches = len([tok for tok in strong_tokens if tok in candidate_tokens])
            weak_matches = len([tok for tok in weak_tokens if tok in candidate_tokens])

            channel_bonus = 0
            if channel_bonus_tokens and channel_bonus_tokens.issubset(_tokenize(uploader)):
                channel_bonus += 2

            score = name_matches * 4 + weak_matches * 1 + channel_bonus
            scored.append((e, score, name_matches))

        if not scored:
            raise NoYouTubeURLFound("ERROR_NO_URL: no scored entries")

        # Sort strictly by score desc
        scored.sort(key=lambda x: x[1], reverse=True)
        
        bad_urls: list[str] = []
        for candidate, score, _ in scored:
            _log(f"Selected candidate score={score}: {candidate.get('title')}")
            candidate_url = _candidate_video_url(candidate)
            if not candidate_url or candidate_url.startswith("ytsearch"):
                continue
            if _is_allowed_youtube_url(candidate_url):
                return candidate_url
            bad_urls.append(candidate_url)

        if bad_urls:
            raise BadYouTubeURL(f"ERROR_BAD_URL: {bad_urls[0]}")
        raise NoYouTubeURLFound("ERROR_NO_URL: no valid youtube url")

    except YouTubeURLResolutionError:
        raise
    except Exception as exc:
        _log(f"Error while searching YouTube: {exc}")
        raise NoYouTubeURLFound("ERROR_NO_URL: unexpected error") from exc


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "alejandro dolina"
    try:
        url = find_youtube_video_url(q)
        print(url)
    except YouTubeURLResolutionError as exc:
        print(str(exc))
