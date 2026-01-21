#!/usr/bin/env python3
"""
Acciones de escritorio disparadas por comandos de voz (texto).

Este módulo no hace STT ni TTS: recibe texto ya transcripto y,
si detecta alguna INTENCIÓN de escritorio, arma un pequeño PLAN
(lista de acciones) y lo ejecuta usando las manos locales
(vía desktop_bridge).

Hoy solo tenemos tool "desktop", pero la estructura ya deja espacio
para agregar tool "web", etc.
"""

from __future__ import annotations

import os
import re
import shlex
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlparse

from lucy_agents.action_router import run_action
from lucy_agents.desktop_bridge import run_desktop_command

PROJECT_ROOT = Path(__file__).resolve().parents[1]
YOUTUBE_CONTROLLER = PROJECT_ROOT / "scripts" / "lucy_youtube_controller.py"
SPOTIFY_CONTROLLER = PROJECT_ROOT / "scripts" / "lucy_spotify_controller.sh"


def _env_bool(name: str, default: bool = True) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    vv = v.strip().lower()
    if vv in {"1", "true", "yes", "y", "on"}:
        return True
    if vv in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v.strip())
    except ValueError:
        return default


def _repo_root() -> Path:
    return PROJECT_ROOT


def _searxng_spoken_summary(query: str, top: int = 3) -> str | None:
    query = (query or "").strip()
    if not query:
        return None

    script = _repo_root() / "scripts" / "searxng_query.py"
    if not script.exists():
        return None

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="lucy_searxng_", suffix=".json", delete=False) as f:
            tmp_path = f.name

        p = subprocess.run(
            [
                sys.executable,
                str(script),
                query,
                "--top",
                str(top),
                "--json-out",
                tmp_path,
            ],
            timeout=8,
            text=True,
            capture_output=True,
        )
        if p.returncode != 0:
            return None

        raw = Path(tmp_path).read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        results = data.get("results") or []

        titles: list[str] = []
        for item in results:
            title = (item.get("title") or "").strip()
            title = title.replace("\n", " ")
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                titles.append(title)
            if len(titles) >= max(0, int(top)):
                break

        if not titles:
            return None

        parts = [f"{i}) {t}." for i, t in enumerate(titles, start=1)]
        return "Encontré: " + " ".join(parts)
    except Exception:  # noqa: BLE001
        return None
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _run_youtube_action(command: str, payload: str) -> dict | None:
    """Execute YouTube actions via the A36 controller CLI."""
    script = str(YOUTUBE_CONTROLLER)
    if not Path(script).exists():
        print(f"[LucyVoiceActions] ERROR_NO_YT_CONTROLLER {script}", file=sys.stderr, flush=True)
        return None

    cmd = [sys.executable, script, command]
    if command == "search":
        cmd.append(payload)
    elif command == "play":
        if "youtube.com" in payload or "youtu.be" in payload:
            cmd.extend(["--url", payload])
        else:
            cmd.extend(["--id", payload])

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        print("[LucyVoiceActions] YouTube controller timeout", file=sys.stderr, flush=True)
        return None

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        msg = stderr if stderr else f"rc={proc.returncode}"
        print(f"[LucyVoiceActions] YouTube controller failed: {msg}", file=sys.stderr, flush=True)
        return None

    out = (proc.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("[LucyVoiceActions] YouTube controller returned invalid JSON", file=sys.stderr, flush=True)
        return None


def _run_spotify_action(command: str, payload: str = "") -> bool:
    """Execute Spotify actions via the local controller script."""
    script = str(SPOTIFY_CONTROLLER)
    if not Path(script).exists():
        print(f"[LucyVoiceActions] ERROR_NO_SPOTIFY_CONTROLLER {script}", file=sys.stderr, flush=True)
        return False

    cmd = [script, command]
    if payload:
        cmd.append(payload)

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
    except subprocess.TimeoutExpired:
        print("[LucyVoiceActions] Spotify controller timeout", file=sys.stderr, flush=True)
        return False

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        msg = stderr if stderr else f"rc={proc.returncode}"
        print(f"[LucyVoiceActions] Spotify controller failed: {msg}", file=sys.stderr, flush=True)
        return False

    return True


def _youtube_action_from_command(command: str) -> tuple[str, str] | None:
    """Translate a desktop xdg-open YouTube command into controller action."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv or argv[0] != "xdg-open" or len(argv) < 2:
        return None
    url = argv[1]
    if "youtube.com" not in url and "youtu.be" not in url:
        return None
    marker = "https://www.youtube.com/results?search_query="
    if marker in url:
        raw = url.split("search_query=", 1)[1].split("&", 1)[0]
        query = unquote_plus(raw).strip()
        return ("search", query) if query else None
    return ("play", url)


def _spotify_action_from_command(command: str) -> tuple[str, str] | None:
    """Translate a desktop xdg-open Spotify command into controller action."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv or argv[0] != "xdg-open" or len(argv) < 2:
        return None
    url = argv[1]

    if url.startswith("spotify:"):
        if url.startswith("spotify:search:"):
            raw = url.split("spotify:search:", 1)[1]
            query = unquote_plus(raw).strip()
            return ("search", query) if query else None
        return ("play_uri", url)

    parsed = urlparse(url)
    if "open.spotify.com" not in (parsed.netloc or ""):
        return None

    if parsed.path.startswith("/search/"):
        raw = parsed.path.split("/search/", 1)[1].strip("/")
        query = unquote_plus(raw).strip()
        return ("search", query) if query else None

    return ("play_uri", url)


def _extract_chatgpt_answer(raw: str) -> str | None:
    matches: list[str] = []
    for line in (raw or "").splitlines():
        m = re.match(r"^\s*LUCY_ANSWER_[0-9_]+:\s*(.+)\s*$", line)
        if not m:
            continue
        val = (m.group(1) or "").strip()
        if val:
            matches.append(val)
    return matches[-1] if matches else None


def _ask_chatgpt_ui(question: str) -> tuple[bool, str]:
    result = run_action("chatgpt_ask", {"prompt": question})
    if not result.get("ok"):
        error = result.get("error") or "unknown error"
        return True, f"No pude ejecutar ChatGPT UI ({error})."

    meta = result.get("meta") or {}
    path = meta.get("path", "UNKNOWN")
    print(f"[LucyVoiceActions] CHATGPT_ROUTER_OK path={path}", file=sys.stderr, flush=True)

    answer_text = (result.get("result", {}).get("answer_text") or "").strip()
    if answer_text:
        return True, answer_text

    return True, "No pude leer la respuesta de ChatGPT."


# =========================
# 1. Modelo de planificación
# =========================


@dataclass
class PlannedAction:
    tool: str  # "desktop" | "youtube" | "spotify" | "web_agent"
    command: str  # comando para el Desktop Agent
    description: str  # para logs humanos (opcional)


# Motor recordado para búsquedas posteriores ("ahora busca X")
LAST_SEARCH_ENGINE: Optional[str] = None  # "google" | "youtube" | "spotify" | "searxng" | None


def _normalize(text: str) -> str:
    """Normaliza texto para matching simple."""
    t = text.lower().strip()
    t = t.replace("luci", "lucy")
    t = " ".join(t.split())
    return t


PLAYBACK_TAILS = (
    " y reproducirlo",
    " y que lo reproduzcas",
    " y que lo pongas",
    " y darle play",
    " y darle play por favor",
    " y reproducir",
    " y reproducirlo por favor",
    " y que lo reproduzcas por favor",
    " y quiero verlo",
    " y quiero ver ese video",
    " y quiero ver el programa",
)


def _fix_common_stt_aliases(q: str) -> str:
    """Normaliza errores típicos del STT en nombres propios/consultas."""
    if not q:
        return q

    fixed = q

    # Variantes típicas de D&D que el STT arruina
    patterns = [
        r"\bred\s+dungeons?\s*(?:&|and)\s*brawns\b",
        r"\bred\s+dungeons?\s+and\s+brawns\b",
        r"\bred\s+and\s+dragons\b",
        r"\bdantions?\s*(?:&|and)\s+dragons\b",
        r"\bcalabozos\s+y\s+dragones\b",
        r"\bdungeons\s+and\s+dragons\b",
        r"\bd\s*&\s*d\b",
        r"\bdnd\b",
    ]

    for pat in patterns:
        fixed = re.sub(pat, "dungeons & dragons", fixed, flags=re.I)

    fixed = re.sub(r"\bn[uú]mero\s+(?:de\s+)?agorio\b", "número áureo", fixed, flags=re.I)

    fixed = re.sub(r"\bn[uú]mero\s+audio\b", "número áureo", fixed, flags=re.I)

    return fixed


def _clean_query(q: str) -> str:
    """Limpia la query de muletillas y espacios."""
    q = q.strip()
    q = re.sub(r"^(?:vos\s+)+", "", q, flags=re.I)
    q = re.sub(r"^(?:en\s+)?la\s+red\s+", "", q, flags=re.I)
    q = re.sub(r"^(?:en\s+)?el\s+red\s+", "", q, flags=re.I)
    q = _fix_common_stt_aliases(q)
    for tail in (" por favor", " porfa", " gracias"):
        if q.endswith(tail):
            q = q[: -len(tail)]
    q_lower = q.lower()
    for tail in PLAYBACK_TAILS:
        if q_lower.endswith(tail):
            q = q[: -len(tail)]
            q_lower = q.lower()
            break
    q = q.strip(" ¿?¡!.,")
    q = re.sub(r"\s+", " ", q)
    # Cortar relleno típico después de la query (ej. 'y me abrís...')
    for pat in (
        r"\s+y\s+me\s+",
        r"\s+y\s+que\s+",
        r"\s+y\s+(?:contame|contarme|contamento|explicame|explicarme|decime|decirme)\b",
    ):
        parts = re.split(pat, q, maxsplit=1)
        if len(parts) > 1:
            q = parts[0].strip()
            break
    return q


def _encode_query(q: str) -> str:
    """Codifica la query para URL usando solo la stdlib."""
    return quote_plus(_clean_query(q))


def _build_google_search_url(query: str) -> str:
    """Arma la URL de búsqueda en Google."""
    encoded = quote_plus(_clean_query(query))
    return f"https://www.google.com/search?q={encoded}"


def _build_searxng_search_url(query: str) -> str:
    """Arma la URL de búsqueda en SearXNG local."""
    base = (os.environ.get("LUCY_SEARXNG_URL") or "http://127.0.0.1:8080").rstrip("/")
    encoded = quote_plus(_clean_query(query))
    return f"{base}/search?q={encoded}&language=es-AR&safesearch=1"


def _has_web_hint(t: str) -> bool:
    # Tolerante a STT: "el red" suele salir en vez de "la red".
    return bool(
        re.search(
            r"\b(?:en\s+la\s+red|la\s+red|en\s+el\s+red|el\s+red|en\s+internet|internet|en\s+la\s+web|la\s+web|web|searx|searxng)\b",
            t,
            flags=re.I,
        )
    )


def _has_chatgpt_hint(t: str) -> bool:
    return bool(re.search(r"\bchat\s*gpt\b", t, flags=re.I))


def _postprocess_chatgpt_query(q: str) -> str:
    q = _clean_query(q)
    if not q:
        return ""
    q = re.sub(r"\s+y\s+dame\b.*$", "", q, flags=re.IGNORECASE).strip()
    q = re.sub(r"\s+y\s+respond(?:e|é|eme|eme)\b.*$", "", q, flags=re.IGNORECASE).strip()
    q = re.sub(r"\s+y\s+decime\b.*$", "", q, flags=re.IGNORECASE).strip()
    return q.strip()


def _extract_chatgpt_query(text: str) -> str:
    if not text or not _has_chatgpt_hint(text):
        return ""

    # Separadores típicos: ":", "-", ","
    sep = r"(?:\s*[:\-–—,]?\s*)"

    patterns = [
        # Caso crítico 1: "preguntale/consultale a chatgpt: X"
        r"(?:pregunt[aá]le|preguntale|consult[aá]le|consultale|averigu[aá]le|averigual[eé])"
        + sep
        + r"(?:a\s+)?chat\s*gpt\b"
        + sep
        + r"(.+)$",
        # Caso crítico 2: "buscá/preguntá/consultá en chatgpt X"
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|pregunt[aá](?:r)?|consult[aá](?:r)?|averigu[aá](?:r)?)"
        + sep
        + r"(?:en\s+)?chat\s*gpt\b"
        + sep
        + r"(.+)$",
        # "abrí chatgpt y buscá/preguntá X"
        r"(?:abr[ií]|abre|abrir)\s+chat\s*gpt\b.*?(?:y\s+)?"
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|pregunt[aá](?:r)?|consult[aá](?:r)?|averigu[aá](?:r)?)"
        r"(?:me|melo|mela|nos|lo|la|le)?" + sep + r"(.+)$",
        # "buscá/preguntá X en chatgpt"
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|pregunt[aá](?:r)?|consult[aá](?:r)?|averigu[aá](?:r)?)"
        r"(?:me|melo|mela|nos|lo|la|le)?" + sep + r"(.+?)\s+(?:en\s+)?chat\s*gpt\b",
        # "en chatgpt buscá/preguntá X"
        r"(?:en\s+)?chat\s*gpt\b.*?"
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|pregunt[aá](?:r)?|consult[aá](?:r)?|averigu[aá](?:r)?)"
        r"(?:me|melo|mela|nos|lo|la|le)?" + sep + r"(.+)$",
        # Fallback voz: "chatgpt, X" / "chat gpt X" (sin verbo)
        r"(?:^|\b)chat\s*gpt\b" + sep + r"(.+)$",
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        q = _postprocess_chatgpt_query(m.group(1))
        # Guardrail: si quedó basura mínima, seguimos probando patrones
        if (q or "").strip().lower() in ("en", "a", "le", "le a"):
            continue
        if q:
            return q
    return ""


def _postprocess_extracted_query(t: str, q: str) -> str:
    """
    Post-procesa queries extraídas para evitar casos típicos de STT truncado:
    - 'buscá en la red' => no debe quedar query='en'
    - elimina engine-hints al inicio ('en la red', 'en la web', 'internet', etc.)
    - recorta coletillas tipo 'y contame brevemente'
    """
    q = (q or "").strip()
    if not q:
        return ""

    # Si el usuario pidió web/red y la "query" quedó en una preposición por STT truncado, descartamos.
    if _has_web_hint(t) and q in ("en", "por"):
        return ""

    # Strip engine-hints al inicio si se colaron en la query.
    q = re.sub(
        r"^(?:en|por)\s*(?:la\s+red|el\s+red|internet|la\s+web|web|searxng|searx)\b\s*",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip()
    q = re.sub(
        r"^(?:la\s+red|el\s+red|internet|la\s+web|web|searxng|searx)\b\s*",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip()

    # Recortar coletillas de resumen si quedaron pegadas.
    q = re.sub(r"\b(y\s+)?contame\b.*$", "", q, flags=re.IGNORECASE).strip()
    q = re.sub(r"\b(y\s+)?brevemente\b.*$", "", q, flags=re.IGNORECASE).strip()
    q = re.sub(r"\b(y\s+)?resum\w*\b.*$", "", q, flags=re.IGNORECASE).strip()

    # Si sigue quedando algo vacío o un token inútil, descartamos.
    if not q or q.lower() in ("en", "por"):
        return ""
    return q


def _extract_web_query(t: str) -> str:
    # Caso A: "buscá en la red X"
    m = re.search(
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(?:en|por)?\s*(?:la\s+red|el\s+red|internet|la\s+web|web|searxng|searx)\s+(.+)",
        t,
    )
    if m:
        q = _clean_query(m.group(1))
        q = _postprocess_extracted_query(t, q)
        return q

    # Caso B: "buscá X en la red"
    m = re.search(
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(.+?)(?:\s+(?:en|por)?\s*(?:la\s+red|el\s+red|internet|la\s+web|web|searxng|searx)\b|$)",
        t,
    )
    if not m:
        return ""
    q = _clean_query(m.group(1))
    q = _postprocess_extracted_query(t, q)
    return q


def _has_search_verb(t: str) -> bool:
    """
    Detecta variantes simples de 'buscar':
    'buscar', 'busca', 'buscá', 'podés buscar', etc.
    """
    return bool(
        re.search(r"\b(?:busc[aá](?:r)?|busqu(?:e|es|en))(?:me|melo|mela|nos|lo|la)?\b", t)
        or re.search(r"\bbokk?a\b", t)
        or "podes buscar" in t
        or "podés buscar" in t
        or "puedes buscar" in t
        or "buscame" in t
        or "buscame" in t
        or "buscáme" in t
    )


def _extract_query_after_buscar(t: str) -> str:
    """
    Extrae lo que viene después de 'buscar'/'busca' en la frase.
    No intenta ser perfecto, solo útil para queries tipo:
      'podés buscar escucho ofertas en youtube'
      'ahora busca escucho ofertas de blender'
    """
    m = re.search(
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(.+)",
        t,
    )
    if not m:
        return ""
    q = _clean_query(m.group(1))
    q = _postprocess_extracted_query(t, q)
    return q


def _extract_query_for_engine(t: str, engine: str) -> str:
    """
    Extrae una query para un motor específico desde texto NORMALIZADO.
    Mantiene heurística simple y determinista.
    """
    engine = (engine or "").strip().lower()
    if engine in ("searx", "searxng", "web", "internet"):
        engine_pat = r"(?:searxng|searx|web|internet|la\s+web|la\s+red|el\s+red)"
    elif engine == "google":
        engine_pat = r"(?:google)"
    elif engine == "youtube":
        engine_pat = r"(?:youtube|you\s*tube)"
    elif engine == "spotify":
        engine_pat = r"(?:spotify)"
    else:
        return ""

    # 1) "buscá X en youtube"
    m = re.search(
        rf"(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(.+?)\s+(?:en|por)?\s*{engine_pat}\b",
        t,
    )
    if m:
        q = _clean_query(m.group(1))
        return _postprocess_extracted_query(t, q)

    # 2) "en youtube buscá X"
    m = re.search(
        rf"(?:^|\s)(?:en|por)?\s*{engine_pat}\b.*?(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(.+)$",
        t,
    )
    if m:
        q = _clean_query(m.group(1))
        return _postprocess_extracted_query(t, q)

    # 3) "abrí youtube y buscá X"
    m = re.search(
        rf"(?:abr[ií]|abre|abrir)\s+{engine_pat}\b.*?(?:y\s+)?(?:busc[aá](?:r)?|busqu(?:e|es|en)|bokk?a)(?:me|melo|mela|nos|lo|la)?\s+(.+)$",
        t,
    )
    if m:
        q = _clean_query(m.group(1))
        return _postprocess_extracted_query(t, q)

    return ""


def _extract_google_query(t: str) -> str:
    """
    Extrae la query pensada para Google justo después de 'busc...'
    y antes de 'en google' si aparece.
    """
    m = re.search(
        r"(?:busc[aá](?:r)?|busqu(?:e|es|en))(?:me|melo|mela|nos|lo|la)?\s+(.+?)(?:\s+(?:en|por)\s+google\b|$)",
        t,
    )
    if not m:
        return ""
    q = _clean_query(m.group(1))
    q = _postprocess_extracted_query(t, q)
    return q


def _extract_spotify_play_query(t: str) -> str:
    """
    Extrae una query para Spotify desde verbos de reproduccion:
    - "pone X en spotify"
    - "reproduci X en spotify"
    - "escucha X en spotify"
    """
    m = re.search(
        r"(?:pon[eé]|pone|poner|reproduc(?:i|í|ir|ime|irme)|escuch[aá])\s+(.+?)\s+(?:en\s+)?spotify\b",
        t,
    )
    if not m:
        return ""
    q = _clean_query(m.group(1))
    q = _postprocess_extracted_query(t, q)
    return q


def _has_open_verb(t: str) -> bool:
    """Detecta verbos de abrir."""
    return bool(
        re.search(
            r"\babr(?:e|i|ir|í|as|ás|amos|ime|eme|ilo|ila|an)?\b",
            t,
        )
    )


def is_complex_youtube_request(text: str) -> bool:
    """
    Devuelve True para pedidos del tipo:
    - 'buscá/quiero la entrevista/programa/charla en YouTube y ponela/reproducila/play'
    Requiere mencionar YouTube + palabra de contenido + verbo de reproducción.
    """
    t = (text or "").lower()

    if "youtube" not in t:
        return False

    has_content = any(
        w in t
        for w in ["entrevista", "programa", "charla", "capítulo", "capitulo", "especial", "video"]
    )
    if not has_content:
        return False

    has_play = any(
        w in t
        for w in [
            "reproduc",
            "poné",
            "pone",
            "ponlo",
            "play",
            "ponerlo",
            "pasá",
            "pasa",
        ]
    )

    return has_play


def _normalize_query_text(text: str) -> str:
    """Limpia muletillas comunes antes de armar la query de búsqueda."""
    t = (text or "").lower()
    fillers = [
        "escuchame",
        "escúchame",
        "quiero que",
        "quiero ",
        "por favor",
        "lucy",
    ]
    for f in fillers:
        t = t.replace(f, " ")
    return " ".join(t.split())


def is_complex_youtube_request(text: str) -> bool:
    """
    Devuelve True para pedidos del tipo 'entrevista/programa en YouTube y reproducilo/play'.
    Requiere: palabra de contenido + verbo de reproducción. YouTube puede ser opcional.
    """
    t = (text or "").lower()

    # Evitar que "no reproducir" dispare el manejo complejo
    if any(
        neg in t
        for neg in (
            "no la reproduzcas",
            "no lo reproduzcas",
            "sin reproducir",
            "no reproducir",
            "solo abrí la búsqueda",
            "solo abre la búsqueda",
            "solo abre la busqueda",
        )
    ):
        return False

    mention_youtube = "youtube" in t or "video" in t
    content_words = [
        "entrevista",
        "programa",
        "especial",
        "mano a mano",
        "charla",
        "capítulo",
        "capitulo",
        "episodio",
    ]
    play_words = [
        "poné",
        "pone",
        "ponlo",
        "reproduce",
        "reproducí",
        "reproducirlo",
        "reproducir",
        "poner play",
        "poné play",
        "pone play",
        "dale play",
        "reproducilo",
        "que se reproduzca",
        "quiero verlo",
        "quiero escucharlo",
        "que la pongas",
        "poneme",
    ]

    has_content = any(w in t for w in content_words)
    has_play = any(w in t for w in play_words)

    if has_content and has_play:
        return True if mention_youtube or has_content else False

    return False


# =========================
# 2. Heurísticas de planning
# =========================


def _augment_searxng_query_for_summary(q: str) -> str:
    """
    Si el usuario pide 'contame/resumen/brevemente', desambiguamos la búsqueda.
    Mantiene 100% heurístico, offline y determinista.
    """
    q = (q or "").strip()
    if not q:
        return q

    # Si ya trae contexto, no tocamos.
    lowered = q.lower()
    if any(
        w in lowered
        for w in ("radio", "podcast", "programa", "episodio", "capitulo", "capítulo", "streaming")
    ):
        return q

    # Entrecomillamos si no viene entre comillas (mejora precisión para nombres).
    if '"' not in q:
        q = f'"{q}"'

    # Agregamos contexto suave (sin OR raro) para mejorar relevancia.
    return f"{q} programa radio podcast"


def _plan_from_text(text: str) -> List[PlannedAction]:
    """
    Dado un texto en castellano, devuelve una lista de acciones
    (posiblemente vacía) que representan lo que Lucy debería hacer
    a nivel escritorio.
    """
    global LAST_SEARCH_ENGINE

    t = _normalize(text)
    actions: List[PlannedAction] = []

    has_search = _has_search_verb(t)
    has_google = "google" in t
    has_youtube = "youtube" in t
    has_spotify = "spotify" in t
    has_web = _has_web_hint(t)

    # ---------- 2.1 Google ----------

    google_query = ""
    if has_google and "busc" in t:
        google_query = _extract_google_query(t)
    if not google_query and (has_search or has_google):
        google_query = _extract_query_for_engine(t, "google")
    if google_query:
        url = _build_google_search_url(google_query)
        actions.append(
            PlannedAction(
                tool="desktop",
                command=f"xdg-open {url}",
                description=f"Abrir Google y buscar '{google_query}'",
            )
        )
        LAST_SEARCH_ENGINE = "google"
    elif has_google and _has_open_verb(t):
        actions.append(
            PlannedAction(
                tool="desktop",
                command="xdg-open https://www.google.com",
                description="Abrir Google en el navegador",
            )
        )
        LAST_SEARCH_ENGINE = "google"

    # ---------- 2.2 YouTube ----------

    youtube_query = _extract_query_for_engine(t, "youtube") if has_search or has_youtube else ""
    if youtube_query:
        encoded = _encode_query(_normalize_query_text(youtube_query))
        url = f"https://www.youtube.com/results?search_query={encoded}"
        actions.append(
            PlannedAction(
                tool="desktop",
                command=f"xdg-open {url}",
                description=f"Abrir YouTube y buscar '{youtube_query}'",
            )
        )
        LAST_SEARCH_ENGINE = "youtube"
    elif has_youtube and _has_open_verb(t):
        actions.append(
            PlannedAction(
                tool="desktop",
                command="xdg-open https://www.youtube.com",
                description="Abrir YouTube en el navegador",
            )
        )
        LAST_SEARCH_ENGINE = "youtube"

    # ---------- 2.2.5 Spotify ----------

    spotify_query = ""
    if has_spotify and (has_search or "pon" in t or "reproduc" in t or "escuch" in t):
        spotify_query = _extract_query_for_engine(t, "spotify") or _extract_spotify_play_query(t)

    if spotify_query:
        actions.append(
            PlannedAction(
                tool="spotify",
                command="search",
                description=spotify_query,
            )
        )
        LAST_SEARCH_ENGINE = "spotify"
    elif has_spotify and _has_open_verb(t):
        actions.append(
            PlannedAction(
                tool="spotify",
                command="open",
                description="Abrir Spotify",
            )
        )
        LAST_SEARCH_ENGINE = "spotify"
    elif has_spotify and any(w in t for w in ("paus", "pause", "deten", "stop")):
        actions.append(
            PlannedAction(
                tool="spotify",
                command="pause",
                description="Pausar Spotify",
            )
        )
    elif has_spotify and any(w in t for w in ("siguiente", "next")):
        actions.append(
            PlannedAction(
                tool="spotify",
                command="next",
                description="Siguiente en Spotify",
            )
        )
    elif has_spotify and any(w in t for w in ("anterior", "prev", "previo")):
        actions.append(
            PlannedAction(
                tool="spotify",
                command="prev",
                description="Anterior en Spotify",
            )
        )
    elif has_spotify and any(w in t for w in ("play", "reproduc", "pon")):
        actions.append(
            PlannedAction(
                tool="spotify",
                command="play",
                description="Reproducir Spotify",
            )
        )

    # ---------- 2.3 Web (SearXNG local) ----------

    searx_query = ""
    if has_search and not has_google and not has_youtube and not has_spotify:
        # Si explícitamente dice web/red/internet, forzamos SearXNG aunque haya motor recordado.
        if has_web or not LAST_SEARCH_ENGINE:
            searx_query = _extract_web_query(t) or _extract_query_after_buscar(t)

    if searx_query:
        if ("contame" in t) or ("breve" in t) or ("resum" in t):
            searx_query = _augment_searxng_query_for_summary(searx_query)
        url = _build_searxng_search_url(searx_query)
        actions.append(
            PlannedAction(
                tool="desktop",
                command=f"xdg-open {url}",
                description=f"Abrir SearXNG y buscar '{searx_query}'",
            )
        )
        LAST_SEARCH_ENGINE = "searxng"
        # Evitar que el bloque 2.3 agregue otra búsqueda duplicada
        has_search = False

    # ---------- 2.3 Buscar usando el último motor recordado ----------

    if has_search and not has_google and not has_youtube and not has_spotify and LAST_SEARCH_ENGINE:
        query = _extract_query_after_buscar(t)
        if query:
            if LAST_SEARCH_ENGINE == "spotify":
                actions.append(
                    PlannedAction(
                        tool="spotify",
                        command="search",
                        description=query,
                    )
                )
            else:
                encoded = _encode_query(query)
                if LAST_SEARCH_ENGINE == "google":
                    url = _build_google_search_url(query)
                    desc = f"Buscar en Google (motor recordado): '{query}'"
                elif LAST_SEARCH_ENGINE == "searxng":
                    url = _build_searxng_search_url(query)
                    desc = f"Buscar en la web (SearXNG, motor recordado): '{query}'"
                else:  # youtube
                    url = f"https://www.youtube.com/results?search_query={encoded}"
                    desc = f"Buscar en YouTube (motor recordado): '{query}'"

                actions.append(
                    PlannedAction(
                        tool="desktop",
                        command=f"xdg-open {url}",
                        description=desc,
                    )
                )

    # ---------- 2.4 Abrir proyecto de Lucy en VS Code ----------

    # Antes: esto se disparaba por "abrí" + "lucy" (y "lucy" está en TODO).
    # Ahora: solo abre VS Code si pedís el proyecto o mencionás VS Code / code explícitamente.
    wants_vscode = (
        "vscode" in t
        or "visual studio code" in t
        or "vs code" in t
        or re.search(r"\bvs\s*code\b", t)
        or re.search(r"\bcode\b", t)
    )
    wants_project = "proyecto" in t and "lucy" in t
    wants_open = bool(re.search(r"\b(abri|abrí|abre|abrir)\b", t))

    if wants_open and (wants_vscode or wants_project):
        actions.append(
            PlannedAction(
                tool="desktop",
                # LUCY_INTENT_OPEN_VSCODE: abrir VS Code en el repo (no depende del cwd)
                command=f"code {shlex.quote(str(PROJECT_ROOT))}",
                description="Abrir el proyecto de Lucy en VS Code",
            )
        )

    # ---------- 2.5 Mostrar / leer README ----------

    if "readme" in t:
        if re.search(r"\b(mostr(a|á)|mostrame|lee|leé|leer)\b", t):
            actions.append(
                PlannedAction(
                    tool="desktop",
                    command="read README.md",
                    description="Leer README.md en la terminal",
                )
            )

    return actions


# =========================
# 3. Orquestador público
# =========================


def _wants_playback(text: str) -> bool:
    """Heurística simple para pedidos de reproducción/play."""
    lowered = text.lower()
    playback_markers = (
        "reproducilo",
        "reproducirlo",
        "reproducir",
        "reproduc",
        "ponelo",
        "ponerlo",
        "pone el programa",
        "poner el programa",
        "pone play",
        "poné play",
        "poné el video",
        "poné ese video",
        "dale play",
        "darle play",
        "quiero verlo",
        "quiero ver ese video",
        "quiero ver el programa",
        "ver el programa",
        "ver ese video",
        "reproduce el programa",
        "reproducí el programa",
        "que lo reproduzcas",
        "quiero ver ese",
    )
    return any(marker in lowered for marker in playback_markers)


def _plan_targets_youtube(plan: list[PlannedAction]) -> bool:
    """Detecta si algún paso apunta a YouTube."""
    for act in plan:
        cmd = act.command.lower()
        desc = act.description.lower()
        if "youtube.com" in cmd or "youtu.be" in cmd or "youtube" in desc:
            return True
    return False


def _extract_youtube_search_query_from_plan(actions: list[PlannedAction]) -> str | None:
    """Recupera la query de búsqueda de YouTube desde el plan generado."""
    for action in actions:
        cmd = (action.command or "").lower()
        marker = "https://www.youtube.com/results?search_query="
        if marker in cmd:
            raw = action.command.split("search_query=", 1)[1]
            raw = raw.split("&", 1)[0]
            query = unquote_plus(raw).strip()
            if query:
                return query
    return None


def _extract_searxng_query_from_plan(actions: list[PlannedAction]) -> str | None:
    base = (os.environ.get("LUCY_SEARXNG_URL") or "http://127.0.0.1:8080").rstrip("/")
    base_netloc = urlparse(base).netloc
    if not base_netloc:
        return None

    for action in actions:
        cmd = action.command or ""
        try:
            argv = shlex.split(cmd)
        except ValueError:
            continue
        if len(argv) < 2:
            continue
        if argv[0] != "xdg-open":
            continue
        url = argv[1]
        parsed = urlparse(url)
        if parsed.netloc != base_netloc:
            continue
        if not parsed.path.startswith("/search"):
            continue
        q = (parse_qs(parsed.query).get("q") or [""])[0].strip()
        if q:
            return q

    return None


def maybe_handle_desktop_intent(text: str) -> bool | tuple[bool, str]:
    """
    Intenta manejar una intención de escritorio a partir de texto.

    - Construye un pequeño plan de acciones.
    - Ejecuta todas las acciones en orden.
    - Devuelve True si hubo al menos una acción, False si no hubo ninguna.

    IMPORTANTE: Se ocupa de tool "desktop" y también de YouTube/Spotify si los detecta.
    """
    text = text or ""
    t = text.strip()
    if not t:
        return False

    lowered = t.lower()
    chatgpt_query = _extract_chatgpt_query(t)
    if chatgpt_query:
        print(
            f"[LucyVoiceActions] Pedido ChatGPT UI detectado; query={chatgpt_query!r}",
            flush=True,
        )
        return _ask_chatgpt_ui(chatgpt_query)

    if any(
        neg in lowered
        for neg in (
            "no la reproduzcas",
            "no lo reproduzcas",
            "sin reproducir",
            "solo abrí la búsqueda",
            "solo abre la busqueda",
            "solo abre la búsqueda",
        )
    ):
        print(
            "[LucyVoiceActions] Pedido de YouTube con 'no reproducir'; se usa plan de escritorio simple.",
            flush=True,
        )
    elif is_complex_youtube_request(text):
        print(
            "[LucyVoiceActions] Pedido complejo de YouTube; se delega al LLM/web_agent.",
            flush=True,
        )
        return None
    elif "youtube" in lowered:
        print(
            "[LucyVoiceActions] Pedido simple de YouTube; se usa plan de escritorio (xdg-open).",
            flush=True,
        )
    elif "spotify" in lowered:
        print(
            "[LucyVoiceActions] Pedido de Spotify detectado; se usa plan local.",
            flush=True,
        )

    plan = _plan_from_text(t)
    if not plan:
        return False

    wants_play = _wants_playback(text)
    yt_last_results: dict | None = None
    yt_last_query: str | None = None

    print("[LucyVoiceActions] plan de escritorio:", flush=True)
    for i, act in enumerate(plan, start=1):
        print(
            f"[LucyVoiceActions]   {i}. [{act.tool}] {act.description} -> {act.command!r}",
            flush=True,
        )

    # Ejecutar en orden
    for act in plan:
        if act.tool == "desktop":
            yt_action = _youtube_action_from_command(act.command)
            if yt_action:
                yt_cmd, yt_payload = yt_action
                result = _run_youtube_action(yt_cmd, yt_payload)
                rc = 0 if result else 3
                if yt_cmd == "search":
                    yt_last_query = yt_payload
                    yt_last_results = result
                print(
                    f"[LucyVoiceActions] Resultado (youtube) {yt_cmd!r} {yt_payload!r}: {rc}",
                    flush=True,
                )
            else:
                sp_action = _spotify_action_from_command(act.command)
                if sp_action:
                    sp_cmd, sp_payload = sp_action
                    ok = _run_spotify_action(sp_cmd, sp_payload)
                    rc = 0 if ok else 3
                    print(
                        f"[LucyVoiceActions] Resultado (spotify) {sp_cmd!r} {sp_payload!r}: {rc}",
                        flush=True,
                    )
                else:
                    rc = run_desktop_command(act.command)
                    print(
                        f"[LucyVoiceActions] Resultado ({act.tool}) {act.command!r}: {rc}",
                        flush=True,
                    )
        elif act.tool in {"youtube", "web_agent"}:
            yt_cmd = "play" if act.command == "play" else "search"
            yt_payload = (act.description or "").strip() or (act.command or "").strip()
            result = _run_youtube_action(yt_cmd, yt_payload)
            rc = 0 if result else 3
            if yt_cmd == "search":
                yt_last_query = yt_payload
                yt_last_results = result
            print(
                f"[LucyVoiceActions] Resultado (youtube) {yt_cmd!r} {yt_payload!r}: {rc}",
                flush=True,
            )
        elif act.tool == "spotify":
            sp_cmd = (act.command or "").strip() or "open"
            sp_payload = (act.description or "").strip()
            if sp_cmd not in {"search", "play_uri"}:
                sp_payload = ""
            ok = _run_spotify_action(sp_cmd, sp_payload)
            rc = 0 if ok else 3
            print(
                f"[LucyVoiceActions] Resultado (spotify) {sp_cmd!r} {sp_payload!r}: {rc}",
                flush=True,
            )
        else:
            print(
                f"[LucyVoiceActions] Tool desconocida {act.tool!r}, "
                f"acción {act.command!r} ignorada.",
                flush=True,
            )

    targets_yt = _plan_targets_youtube(plan)
    targets_web = any("/search?q=" in (act.command or "") for act in plan)
    searx_query_from_plan = _extract_searxng_query_from_plan(plan)

    if targets_web and not targets_yt and not wants_play:
        spoken = "Te abrí la búsqueda en la web."
        if searx_query_from_plan and _env_bool("LUCY_SEARXNG_SUMMARY", default=True):
            summary = _searxng_spoken_summary(searx_query_from_plan, top=3)
            if summary:
                spoken = f"{summary} Te abrí la búsqueda en la web."
        return True, spoken

    if wants_play and targets_yt:
        search_query = _extract_youtube_search_query_from_plan(plan) or text.strip()
        print(
            f"[LucyVoiceActions] Playback intent detected for YouTube; query={search_query!r}",
            flush=True,
        )
        result = yt_last_results or _run_youtube_action("search", search_query)
        results_list = []
        if isinstance(result, dict):
            results_list = result.get("results") or []
        if not results_list:
            spoken = (
                "No pude leer resultados de YouTube para reproducir en este momento."
            )
            return True, spoken

        first = results_list[0] or {}
        video_id = (first.get("id") or "").strip()
        if not video_id:
            spoken = "No pude identificar un video válido para reproducir."
            return True, spoken

        play_result = _run_youtube_action("play", video_id)
        if not play_result:
            spoken = "Falló el intento de reproducción en YouTube."
            return True, spoken

        spoken = "Te abrí la búsqueda y además el primer video en YouTube."
        return True, spoken

    return True


if __name__ == "__main__":
    # Pequeño test manual (no se usa en producción):
    tests = [
        "podés abrir Google?",
        "abrí youtube y buscá escucho ofertas de blender",
        "ahora buscá escucho ofertas de blender",
        "bien quiero que ahora abras youtube que ahora se escucho ofertas y me abras el programa transmitido hace dos días",
        "puedes buscar noticias sobre constantinopla en google",
        "abrí el proyecto de lucy y mostrame el readme",
        "esto no debería disparar nada",
    ]
    for t in tests:
        print(f"\n>>> {t!r}")
        handled = maybe_handle_desktop_intent(t)
        print(f"handled = {handled}")
