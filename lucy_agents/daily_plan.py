#!/usr/bin/env python3
"""Local-first daily plan builder."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 12].rstrip() + "... (truncated)"


def _resolve_plan_path() -> Path | None:
    env_setting = os.environ.get("LUCY_DAILY_PLAN_FILE")
    if env_setting:
        candidate = Path(env_setting).expanduser()
        if candidate.is_file():
            return candidate

    user_path = Path.home() / ".local" / "share" / "lucy" / "daily_plan.md"
    if user_path.is_file():
        return user_path

    repo_path = PROJECT_ROOT / "docs" / "daily_plan.md"
    if repo_path.is_file():
        return repo_path

    return None


def _today_str() -> str:
    return date.today().isoformat()


def _offline_plan(date_str: str) -> str:
    lines = [
        f"Plan del dia ({date_str})",
        "",
        "Bloque 1 (09:00-11:00): trabajo profundo (tarea principal)",
        "Bloque 2 (11:15-12:30): tareas rapidas y pendientes",
        "Bloque 3 (14:00-16:00): proyecto principal / avance clave",
        "Bloque 4 (16:15-17:00): cierre, notas y siguiente paso",
        "",
        "Checklist:",
        "- [ ] Elegir 1 objetivo principal",
        "- [ ] Definir 2 tareas de soporte",
        "- [ ] Revisar pendientes criticos",
        "- [ ] Preparar cierre del dia",
    ]
    return "\n".join(lines)


def get_base_plan(date_str: str | None, max_chars: int = 2500) -> Tuple[str, str]:
    date_value = date_str or _today_str()
    path = _resolve_plan_path()
    if path:
        text = _read_text(path)
        return _trim_text(text, max_chars), "FILE"
    text = _offline_plan(date_value)
    return _trim_text(text, max_chars), "OFFLINE"


def build_chatgpt_prompt(base_plan: str, date_str: str | None, prompt_hint: str, max_chars: int) -> str:
    date_value = date_str or _today_str()
    hint_block = f"Hint: {prompt_hint}\n" if prompt_hint else ""
    prompt = (
        "Mejora este plan base del dia en espanol."
        " Mantenelo breve, claro y accionable."
        f" Limite aproximado: {max_chars} caracteres.\n"
        "No agregues introduccion ni cierre, solo el plan.\n"
        f"Fecha: {date_value}.\n"
        f"{hint_block}"
        "Plan base:\n"
        f"{base_plan}"
    )
    return prompt
