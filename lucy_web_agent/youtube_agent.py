import json
import re
import subprocess
import unicodedata
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus


def _log(msg: str) -> None:
    print(f"[LucyWebAgent] {msg}", flush=True)


KEYWORD_BONUS = ("entrevista", "programa", "capítulo", "capitulo", "especial")
COMMON_WORDS = {"entrevista", "programa", "video", "completo", "canal", "especial", "capitulo", "capítulo", "charla"}
MISHEAR_REPLACEMENTS = {
    "navaricio": "novaresio",
    "navarrecio": "novaresio",
    "navarricio": "novaresio",
    "novaricio": "novaresio",
    "navaricio": "novaresio",
    "navarrecio": "novaresio",
    "navarro": "navarro",
    "roberto navarro": "navarro",
    "delina": "dolina",
    "donina": "dolina",
    "adolino": "dolina",
    "adolína": "dolina",
}
STRONG_PEOPLE = {"dolina", "novaresio", "navarro"}
STRONG_WORDS = {"entrevista", "mano a mano", "programa", "charla"}


def _normalize_token(t: str) -> str:
    """
    Normaliza un token para comparación.
    - minúsculas
    - quitar tildes
    - quitar caracteres no alfabéticos
    - recortar espacios
    """
    if not t:
        return ""
    norm = unicodedata.normalize("NFD", t.lower())
    norm = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    norm = re.sub(r"[^a-z0-9]+", " ", norm).strip()
    return norm


def _fix_mishearings(text: str) -> str:
    """Aplica reemplazos comunes de STT para nombres propios."""
    fixed = text.lower()
    for wrong, right in MISHEAR_REPLACEMENTS.items():
        fixed = fixed.replace(wrong, right)
    return fixed


def _strong_query_tokens(query: str) -> list[str]:
    """Devuelve tokens relevantes (>=4 chars y no palabras comunes)."""
    tokens: list[str] = []
    normalized = _normalize_token(_fix_mishearings(query))
    for raw in re.split(r"\s+", normalized):
        tok = raw.strip()
        if len(tok) >= 4 and tok not in COMMON_WORDS:
            tokens.append(tok)
    return tokens


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.split(r"\s+", _normalize_token(text)) if tok}


def _score_candidate(entry: Dict[str, Any], strong_tokens: list[str]) -> int:
    """Calcula un puntaje heurístico para un video."""
    title = _fix_mishearings(entry.get("title") or "")
    uploader = _fix_mishearings(entry.get("uploader") or entry.get("channel") or "")

    title_tokens = _tokenize(title)
    channel_tokens = _tokenize(uploader)

    title_matches = {tok for tok in strong_tokens if tok in title_tokens}
    channel_matches = {tok for tok in strong_tokens if tok in channel_tokens}

    if not title_matches and not channel_matches:
        return -1  # descartar candidatos sin coincidencias fuertes

    score = len(title_matches) * 2 + len(channel_matches) * 1

    if "entrevista" in title_tokens:
        score += 1

    if len(title_matches) >= 2:
        score += 2

    if len(strong_tokens) >= 2 and all(tok in title_tokens for tok in strong_tokens[:2]):
        score += 3

    # Bonos específicos para combinaciones fuertes
    if "dolina" in title_tokens and "novaresio" in title_tokens:
        score += 4
    if "dolina" in title_tokens and "navarro" in title_tokens:
        score += 3
    if "entrevista" in title_tokens and any(p in title_tokens for p in STRONG_PEOPLE):
        score += 2

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


def find_youtube_video_url(
    query: str,
    channel_hint: Optional[str] = None,
    strategy: str = "latest",
) -> Optional[str]:
    """
    Dado un texto de búsqueda y (opcionalmente) un identificador/dica de canal,
    intenta encontrar una URL de video de YouTube que encaje.

    Por ahora solo define la interfaz.
    La implementación real podrá usar Playwright, Selenium, o un cliente HTTP.

    Estrategias posibles:
    - "latest": el video más reciente que encaje con la búsqueda.
    - "live_or_latest": si hay vivo, usar ese; si no, el último video.

    Devuelve:
    - Una URL completa de YouTube (https://www.youtube.com/watch?v=...)
      si tuvo éxito.
    - None si no pudo encontrar nada aceptable.
    """
    try:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            _log("Empty query provided to find_youtube_video_url.")
            return None

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
        if proc.returncode != 0:
            _log(f"yt-dlp failed (code {proc.returncode}): {proc.stderr.strip()}")
            return None

        stdout = proc.stdout or ""
        if not stdout.strip():
            _log("yt-dlp returned empty output.")
            return None

        data = json.loads(stdout)
        entries = data.get("entries") or []
        if not entries and isinstance(data, dict) and "webpage_url" in data:
            entries = [data]

        if not entries:
            _log(f"[LucyWebAgent] Sin resultados de yt-dlp para query='{cleaned_query}', channel_hint='{channel_hint}'")
            return None

        strong_tokens = _strong_query_tokens(cleaned_query)
        if channel_hint:
            strong_tokens.extend(_strong_query_tokens(channel_hint))

        scored: list[tuple[Dict[str, Any], int]] = []
        for e in entries:
            score = _score_candidate(e, strong_tokens)
            if score >= 0:
                scored.append((e, score))

        if not scored:
            _log(f"[LucyWebAgent] Sin candidatos con tokens fuertes para query='{cleaned_query}'.")
        else:
            _log(f"[LucyWebAgent] Puntajes candidatos: {[(e.get('title'), s) for e, s in scored]}")

        scored_sorted = sorted(scored, key=lambda pair: pair[1], reverse=True)

        candidate = scored_sorted[0][0] if scored_sorted else None
        best_score = scored_sorted[0][1] if scored_sorted else 0

        if not candidate or best_score < 3:
            search_url = f"https://www.youtube.com/results?search_query={quote_plus(cleaned_query)}"
            _log(f"[LucyWebAgent] No hay candidato claro, devolviendo search_url genérico: {search_url}")
            return search_url

        url = (
            candidate.get("webpage_url")
            or candidate.get("url")
            or (f"https://www.youtube.com/watch?v={candidate['id']}" if candidate.get("id") else None)
        )

        title = candidate.get("title") or "(sin título)"
        uploader = candidate.get("uploader") or candidate.get("channel") or "(sin canal)"
        _log(f"[LucyWebAgent] Elegí video: titulo='{title}', canal='{uploader}', url='{url}'")

        return url

    except Exception as exc:
        _log(f"Error while searching YouTube: {exc}")
        return None


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "alejandro dolina"
    url = find_youtube_video_url(q)
    if url:
        print(url)
    else:
        print("No se encontró ningún video para esa búsqueda.")
