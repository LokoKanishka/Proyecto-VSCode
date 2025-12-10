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

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote_plus, unquote_plus

from lucy_agents.desktop_bridge import run_desktop_command
from lucy_web_agent import find_youtube_video_url


# =========================
# 1. Modelo de planificación
# =========================

@dataclass
class PlannedAction:
    tool: str          # por ahora siempre "desktop"
    command: str       # comando para el Desktop Agent
    description: str   # para logs humanos (opcional)


# Motor recordado para búsquedas posteriores ("ahora busca X")
LAST_SEARCH_ENGINE: Optional[str] = None  # "google" | "youtube" | None


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


def _clean_query(q: str) -> str:
    """Limpia la query de muletillas y espacios."""
    q = q.strip()
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
    for pat in (r"\s+y\s+me\s+", r"\s+y\s+que\s+"):
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


def _has_search_verb(t: str) -> bool:
    """
    Detecta variantes simples de 'buscar':
    'buscar', 'busca', 'buscá', 'podés buscar', etc.
    """
    return bool(re.search(r"\bbusc[aá](?:r)?\b", t) or "podes buscar" in t or "podés buscar" in t or "puedes buscar" in t)


def _extract_query_after_buscar(t: str) -> str:
    """
    Extrae lo que viene después de 'buscar'/'busca' en la frase.
    No intenta ser perfecto, solo útil para queries tipo:
      'podés buscar escucho ofertas en youtube'
      'ahora busca escucho ofertas de blender'
    """
    m = re.search(r"busc[aá](?:r)?\s+(.+)", t)
    if not m:
        return ""
    return _clean_query(m.group(1))


def _extract_query_for_engine(t: str, engine: str) -> str:
    """
    Busca patrones explícitos para un motor concreto (google/youtube).
    Ejemplos:
      - 'buscá X en youtube'
      - 'abrí youtube y buscá X'
    """
    patterns = [
        rf"{engine}[^\n]*?busc[aá](?:r)?\s+(.+)",                     # ...youtube... buscá X
        rf"busc[aá](?:r)?\s+(?:en|por)\s+{engine}\s+(.+)",           # buscá en youtube X
        rf"busc[aá](?:r)?\s+(.+?)\s+(?:en|por)\s+{engine}",           # buscá X en youtube
        rf"ahora[^\n]*?busc[aá](?:r)?\s+(.+?)\s+(?:en|por)\s+{engine}",  # ahora buscá X en youtube
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            return _clean_query(m.group(1))
    return ""


def _extract_google_query(t: str) -> str:
    """
    Extrae la query pensada para Google justo después de 'busc...'
    y antes de 'en google' si aparece.
    """
    m = re.search(r"busc[aá](?:r)?\s+(.+?)(?:\s+(?:en|por)\s+google\b|$)", t)
    if not m:
        return ""
    return _clean_query(m.group(1))


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
        w in t for w in ["entrevista", "programa", "charla", "capítulo", "capitulo", "especial", "video"]
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
    if any(neg in t for neg in ("no la reproduzcas", "no lo reproduzcas", "sin reproducir", "no reproducir", "solo abrí la búsqueda")):
        return False

    mention_youtube = "youtube" in t
    content_words = ["entrevista", "programa", "especial", "mano a mano", "charla", "capítulo", "capitulo", "episodio"]
    play_words = ["poné", "pone", "ponlo", "reproduce", "reproducí", "reproducirlo", "poner play", "dale play", "reproducilo", "reproducir"]

    has_content = any(w in t for w in content_words)
    has_play = any(w in t for w in play_words)

    if has_content and has_play:
        return True if mention_youtube or has_content else False

    return False


# =========================
# 2. Heurísticas de planning
# =========================

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

    # ---------- 2.3 Buscar usando el último motor recordado ----------

    if has_search and not has_google and not has_youtube and LAST_SEARCH_ENGINE:
        query = _extract_query_after_buscar(t)
        if query:
            encoded = _encode_query(query)
            if LAST_SEARCH_ENGINE == "google":
                url = _build_google_search_url(query)
                desc = f"Buscar en Google (motor recordado): '{query}'"
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

    if (
        "abrí" in t
        or "abre" in t
        or "abrir" in t
        or "abri " in t
        or "vscode" in t
        or "visual studio code" in t
    ):
        if (
            "proyecto" in t
            or "lucy" in t
            or "código" in t
            or "codigo" in t
            or "code" in t
        ):
            actions.append(
                PlannedAction(
                    tool="desktop",
                    command="code .",
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


def maybe_handle_desktop_intent(text: str) -> bool | tuple[bool, str]:
    """
    Intenta manejar una intención de escritorio a partir de texto.

    - Construye un pequeño plan de acciones.
    - Ejecuta todas las acciones en orden.
    - Devuelve True si hubo al menos una acción, False si no hubo ninguna.

    IMPORTANTE: Solo se ocupa de tool "desktop".
    """
    text = text or ""
    t = text.strip()
    if not t:
        return False

    lowered = t.lower()
    if any(neg in lowered for neg in ("no la reproduzcas", "no lo reproduzcas", "sin reproducir", "solo abrí la búsqueda", "solo abre la busqueda", "solo abre la búsqueda")):
        print("[LucyVoiceActions] Pedido de YouTube con 'no reproducir'; se usa plan de escritorio simple.", flush=True)
    elif is_complex_youtube_request(text):
        print(
            "[LucyVoiceActions] Pedido complejo de YouTube (entrevista/programa + reproducir); se delega al LLM/web_agent.",
            flush=True,
        )
        return None
    elif "youtube" in lowered:
        print(
            "[LucyVoiceActions] Pedido de YouTube simple o sin verbo de reproducción; se usa plan de escritorio.",
            flush=True,
        )

    plan = _plan_from_text(t)
    if not plan:
        return False

    wants_play = _wants_playback(text)

    print("[LucyVoiceActions] plan de escritorio:", flush=True)
    for i, act in enumerate(plan, start=1):
        print(
            f"[LucyVoiceActions]   {i}. [{act.tool}] {act.description} -> {act.command!r}",
            flush=True,
        )

    # Ejecutar en orden
    for act in plan:
        if act.tool == "desktop":
            rc = run_desktop_command(act.command)
            print(
                f"[LucyVoiceActions] Resultado ({act.tool}) {act.command!r}: {rc}",
                flush=True,
            )
        else:
            print(
                f"[LucyVoiceActions] Tool desconocida {act.tool!r}, "
                f"acción {act.command!r} ignorada.",
                flush=True,
            )

    targets_yt = _plan_targets_youtube(plan)

    if wants_play and targets_yt:
        search_query = _extract_youtube_search_query_from_plan(plan) or text.strip()
        print(
            f"[LucyVoiceActions] Playback intent detected for YouTube; query={search_query!r}",
            flush=True,
        )
        video_url = find_youtube_video_url(search_query, channel_hint=None, strategy="latest")
        if video_url:
            print(
                f"[LucyVoiceActions] Web agent selected YouTube video URL: {video_url}",
                flush=True,
            )
            cmd = f"xdg-open {video_url}"
            rc = run_desktop_command(cmd)
            print(f"[LucyVoiceActions] Resultado (desktop) {cmd!r}: {rc}", flush=True)
            if isinstance(video_url, str) and video_url.startswith("https://www.youtube.com/results?search_query="):
                spoken = "No encontré una entrevista exacta, pero te abrí la búsqueda en YouTube para que elijas."
            else:
                spoken = "Te abrí la búsqueda y además un video en YouTube. Debería estar reproduciéndose en otra pestaña."
            return True, spoken
        else:
            print(
                f"[LucyVoiceActions] Web agent could not select a YouTube video for query: {search_query!r}",
                flush=True,
            )
            spoken = (
                "Te abrí la búsqueda en YouTube para ese programa, pero todavía no puedo "
                "elegir el video ni darle play. Tenés que apretar vos en el que quieras."
            )
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
