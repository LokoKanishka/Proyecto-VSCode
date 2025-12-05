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
from typing import List

from lucy_agents.desktop_bridge import run_desktop_command


# =========================
# 1. Modelo de planificación
# =========================

@dataclass
class PlannedAction:
    tool: str          # por ahora siempre "desktop"
    command: str       # comando para el Desktop Agent
    description: str   # para logs humanos (opcional)


def _normalize(text: str) -> str:
    """Normaliza texto para matching simple."""
    t = text.lower().strip()
    t = t.replace("luci", "lucy")
    return t


# =========================
# 2. Heurísticas de planning
# =========================

def _plan_from_text(text: str) -> List[PlannedAction]:
    """
    Dado un texto en castellano, devuelve una lista de acciones
    (posiblemente vacía) que representan lo que Lucy debería hacer
    a nivel escritorio.
    """
    t = _normalize(text)
    actions: List[PlannedAction] = []

    # --- 2.1 Abrir Google (navegador) ---
    # Cubre: "abrí / podés abrir google", "abrir el navegador", etc.
    if ("google" in t or "navegador" in t or "browser" in t) and any(
        v in t for v in ("abr", "pod", "pued")
    ):
        actions.append(
            PlannedAction(
                tool="desktop",
                command="xdg-open https://www.google.com",
                description="Abrir Google en el navegador",
            )
        )

    # --- 2.2 Abrir YouTube ---
    if "youtube" in t and any(v in t for v in ("abr", "pod", "pued")):
        actions.append(
            PlannedAction(
                tool="desktop",
                command="xdg-open https://www.youtube.com",
                description="Abrir YouTube en el navegador",
            )
        )

    # --- 2.3 Abrir proyecto de Lucy en VS Code ---
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

    # --- 2.4 Mostrar / leer README ---
    if "readme" in t:
        if re.search(r"\b(mostr(a|á)|mostrame|lee|leé|leer)\b", t):
            actions.append(
                PlannedAction(
                    tool="desktop",
                    command="read README.md",
                    description="Leer README.md en la terminal",
                )
            )

    # En el futuro, acá podemos agregar:
    # - tool="web" para disparar el web-agent con una query
    # - otros comandos de escritorio (capturas, abrir docs, etc.)

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
            # Placeholder para futuros tools (web, etc.)
            print(
                f"[LucyVoiceActions] Tool desconocida {act.tool!r}, "
                f"acción {act.command!r} ignorada."
            )

    return True


if __name__ == "__main__":
    # Pequeño test manual (no se usa en producción):
    tests = [
        "podés abrir Google?",
        "primero abrí Google y después abrí YouTube",
        "abrí el proyecto de lucy",
        "mostrame el readme",
        "esto no debería disparar nada",
    ]
    for t in tests:
        print(f"\n>>> {t!r}")
        handled = maybe_handle_desktop_intent(t)
        print(f"handled = {handled}")
