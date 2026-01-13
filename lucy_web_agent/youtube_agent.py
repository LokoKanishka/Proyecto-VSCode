import json
import re
import subprocess
import unicodedata
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus


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
        if "youtube.com/watch?v=" in url:
            _log(f"Fallback: Found URL {url}")
            return url
            
    return None

def find_youtube_video_url(
    query: str,
    channel_hint: Optional[str] = None,
    strategy: str = "latest",
) -> Optional[str]:
    """
    Dado un texto de búsqueda y (opcionalmente) un identificador/dica de canal,
    intenta encontrar una URL de video de YouTube que encaje.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        _log("Empty query provided to find_youtube_video_url.")
        return None
        
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(cleaned_query)}"

    # 1. Check yt-dlp availability
    if not shutil.which("yt-dlp"):
         _log("yt-dlp not found. Trying SearXNG fallback.")
         fallback = _search_searxng_fallback(cleaned_query)
         if fallback:
             return fallback
         return search_url

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
            return search_url

        stdout = proc.stdout or ""
        if not stdout.strip():
            _log("yt-dlp returned empty output. Trying SearXNG fallback.")
            fallback = _search_searxng_fallback(cleaned_query)
            if fallback:
                 return fallback
            return search_url

        data = json.loads(stdout)
        entries = data.get("entries") or []
        if not entries and isinstance(data, dict) and "webpage_url" in data:
            entries = [data]

        if not entries:
            _log(f"[LucyWebAgent] No entries from yt-dlp. Returning generic.")
            return search_url

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
             return search_url

        # Sort strictly by score desc
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_candidate = scored[0][0]
        best_score = scored[0][1]
        
        _log(f"Selected best candidate score={best_score}: {best_candidate.get('title')}")

        video_url: str | None = None
        if best_candidate.get("webpage_url"):
            video_url = best_candidate.get("webpage_url")
        elif best_candidate.get("url"):
            raw = best_candidate.get("url")
            if isinstance(raw, str) and raw.startswith(("http://", "https://")):
                video_url = raw
            elif isinstance(raw, str) and not raw.startswith("ytsearch"):
                video_url = f"https://www.youtube.com/watch?v={raw}"
        elif best_candidate.get("id"):
            video_url = f"https://www.youtube.com/watch?v={best_candidate.get('id')}"

        if not video_url or (isinstance(video_url, str) and video_url.startswith("ytsearch")):
            return search_url

        return video_url

    except Exception as exc:
        _log(f"Error while searching YouTube: {exc}")
        return search_url


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "alejandro dolina"
    url = find_youtube_video_url(q)
    if url:
        print(url)
    else:
        print("No se encontró ningún video para esa búsqueda.")
