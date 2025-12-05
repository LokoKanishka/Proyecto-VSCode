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
from urllib.parse import quote_plus

from lucy_agents.desktop_bridge import run_desktop_command


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


def _clean_query(q: str) -> str:
    """Limpia la query de muletillas y espacios."""
    q = q.strip()
    for tail in (" por favor", " porfa", " gracias"):
        if q.endswith(tail):
            q = q[: -len(tail)]
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
        rf"busc[aá](?:r)?\s+(.+?)\s+(?:en|por)\s+{engine}",           # buscá X en youtube
        rf"ahora[^\n]*?busc[aá](?:r)?\s+(.+?)\s+(?:en|por)\s+{engine}",  # ahora buscá X en youtube
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            return _clean_query(m.group(1))
    return ""


def _has_open_verb(t: str) -> bool:
    """Detecta verbos de abrir."""
    return bool(
        re.search(
            r"\babr(?:e|i|ir|í|as|ás|amos|ime|eme|ilo|ila|an)?\b",
            t,
        )
    )


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

    google_query = _extract_query_for_engine(t, "google") if has_search or has_google else ""
    if google_query:
        encoded = _encode_query(google_query)
        url = f"https://www.google.com/search?q={encoded}"
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
        encoded = _encode_query(youtube_query)
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
                url = f"https://www.google.com/search?q={encoded}"
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

def maybe_handle_desktop_intent(text: str) -> bool:
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

    plan = _plan_from_text(t)
    if not plan:
        return False

    print("[LucyVoiceActions] Plan de escritorio generado:")
    for i, act in enumerate(plan, start=1):
        print(f"  {i}. [{act.tool}] {act.description} -> {act.command!r}")

    # Ejecutar en orden
    for act in plan:
        if act.tool == "desktop":
            rc = run_desktop_command(act.command)
            print(
                f"[LucyVoiceActions] Resultado ({act.tool}) {act.command!r}: {rc}"
            )
        else:
            print(
                f"[LucyVoiceActions] Tool desconocida {act.tool!r}, "
                f"acción {act.command!r} ignorada."
            )

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
