#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


MARKER = "LUCY_STT_JUNK_FILTER"


def _insert_helper_after_imports(source: str) -> str:
    if "_lucy_is_junk_stt" in source:
        return source

    lines = source.splitlines(True)
    last_import = -1
    for i, line in enumerate(lines[:300]):
        if re.match(r"^\s*(from|import)\s+\w+", line):
            last_import = i

    helper = f"""
# --- {MARKER}: evita ruido tipo “Amara.org”, “Suscribite”, etc. ---
_LUCY_JUNK_STT_PATTERNS = [
    r"subt[ií]tulos\\s+por\\s+la\\s+comunidad\\s+de\\s+amara\\.org",
    r"^\\s*(?:¡)?suscr[ií]b(?:i|í)te(?:!)?\\s*$",
]


def _lucy_is_junk_stt(text: str) -> bool:
    t = (text or \"\").strip()
    if not t:
        return False
    for pat in _LUCY_JUNK_STT_PATTERNS:
        if re.search(pat, t, flags=re.I):
            return True
    return False
"""

    insert_at = (last_import + 1) if last_import >= 0 else 0
    lines.insert(insert_at, helper + "\n")
    return "".join(lines)


def _insert_guard_before_stt_log(source: str) -> str:
    if "STT junk ignorado" in source:
        return source

    pattern = re.compile(
        r"^(?P<indent>\s*)_log\(\s*f?[\"']\[LucyVoice\]\s+STT\s+text:\s*\{text!r\}[\"']\s*\)\s*$",
        flags=re.M,
    )
    match = pattern.search(source)
    if not match:
        raise SystemExit(
            "No pude encontrar la línea de log `_log(f\"[LucyVoice] STT text: {text!r}\")` para insertar el guard."
        )

    indent = match.group("indent")
    guard = (
        f"{indent}if _lucy_is_junk_stt(text):\n"
        f"{indent}    _log(f\"[LucyVoice] STT junk ignorado: {{text!r}}\")\n"
        f"{indent}    continue\n"
    )

    return source[: match.start()] + guard + source[match.start() :]


def main() -> int:
    app_path = Path(os.environ.get("LUCY_VOICE_APP_PATH", "app.py"))
    if not app_path.is_file():
        print(f"[{MARKER}] ERROR: no existe {app_path}", file=sys.stderr)
        return 2

    source = app_path.read_text(encoding="utf-8", errors="replace")
    if MARKER not in source:
        try:
            source = _insert_helper_after_imports(source)
            source = _insert_guard_before_stt_log(source)
        except Exception as exc:
            print(f"[{MARKER}] WARN: no se pudo aplicar el filtro ({exc}); ejecutando sin filtro.", file=sys.stderr)
            source = app_path.read_text(encoding="utf-8", errors="replace")

    code = compile(source, str(app_path), "exec")
    glb = {"__name__": "__main__", "__file__": str(app_path), "__package__": None}
    exec(code, glb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
