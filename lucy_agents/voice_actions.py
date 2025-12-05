#!/usr/bin/env python3
"""
Acciones de escritorio disparadas por comandos de voz (texto).

Este módulo no hace STT ni TTS: recibe texto ya transcripto y,
si detecta alguna intención de escritorio, llama a las manos locales
(vía desktop_bridge) y devuelve True. Si no reconoce nada, devuelve False.
"""

from __future__ import annotations

import re
from typing import Optional

from lucy_agents.desktop_bridge import run_desktop_command

# --- Utilidades de normalización ---


def _normalize(text: str) -> str:
    """Normaliza texto para matching simple."""
    t = text.lower().strip()
    # Normalizar variantes de 'lucy' con y/i al final, etc.
    t = t.replace("luci", "lucy")
    return t


# --- Intenciones concretas ---


def _intent_open_project(text: str) -> Optional[str]:
    """
    Intención: abrir el proyecto Lucy en VS Code.

    Frases esperadas (ejemplos):
      - "abrí el proyecto"
      - "abrí el proyecto de lucy"
      - "abrí vscode"
      - "abrí visual studio code"
      - "abrí el código"
    """
    t = _normalize(text)

    # Reglas muy simples para empezar
    if "abrí" in t or "abre" in t or "abrir" in t:
        if "proyecto" in t or "lucy" in t or "código" in t or "code" in t:
            return "code ."

    if "vscode" in t or "visual studio code" in t:
        return "code ."

    return None


def _intent_open_readme(text: str) -> Optional[str]:
    """
    Intención: mostrar el README en la terminal.

    Frases esperadas:
      - "mostrame el readme"
      - "leé el readme"
      - "leé el archivo readme"
    """
    t = _normalize(text)

    if "readme" in t:
        # Aceptamos "mostrá", "leé", "lee", etc.
        if re.search(r"\bmostr(a|á)|lee|leé|leer\b", t):
            return "read README.md"

    return None


# --- Orquestador ---


def maybe_handle_desktop_intent(text: str) -> bool:
    """
    Intenta manejar una intención de escritorio a partir de texto.

    Devuelve True si ejecutó alguna acción (aunque falle el comando),
    False si no reconoció ninguna intención.
    """
    text = text or ""
    t = text.strip()
    if not t:
        return False

    # 1) Probar intenciones específicas
    for handler in (_intent_open_project, _intent_open_readme):
        cmd = handler(t)
        if cmd:
            print(f"[LucyVoiceActions] Intención de escritorio detectada: {cmd!r}")
            rc = run_desktop_command(cmd)
            print(f"[LucyVoiceActions] Resultado comando {cmd!r}: {rc}")
            return True

    # 2) Nada reconocido
    return False


if __name__ == "__main__":
    # Pequeño test manual:
    tests = [
        "abrí el proyecto de lucy",
        "abrí vscode",
        "mostrame el readme",
        "leé el archivo README por favor",
        "esto no debería disparar nada",
    ]
    for t in tests:
        print(f"\n>>> {t!r}")
        handled = maybe_handle_desktop_intent(t)
        print(f"handled = {handled}")
