#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

TARGET_EXTS = {".py", ".sh", ".bash", ".zsh", ".js", ".ts"}

NULL_REDIRECT_RE = re.compile(
    r"""
    (?:^|[ \t])
    (?:
        &>\s*/dev/null |
        >\s*/dev/null |
        1>\s*/dev/null |
        2>\s*/dev/null |
        >/dev/null |
        2>/dev/null |
        1>/dev/null
    )
""",
    re.VERBOSE,
)


@dataclass
class Finding:
    file: str
    line: int
    kind: str
    risk: str
    snippet: str
    detail: str


def expr_to_str(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Attribute):
        return f"{expr_to_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        fn = expr_to_str(node.func)
        args = []
        for a in node.args[:2]:
            args.append(expr_to_str(a))
        if len(node.args) > 2:
            args.append("…")
        return f"{fn}({', '.join(args)})"
    if isinstance(node, ast.Subscript):
        return f"{expr_to_str(node.value)}[{expr_to_str(node.slice)}]"
    return node.__class__.__name__


def is_true_const(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def kw_value_node(call: ast.Call, name: str) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def looks_like_devnull(node: Optional[ast.AST]) -> bool:
    if node is None:
        return False
    s = expr_to_str(node)
    if "DEVNULL" in s:
        return True
    if "os.devnull" in s or "os.devnull" in s.replace(" ", ""):
        return True
    if s.startswith("open(") and "devnull" in s.lower():
        return True
    return False


def looks_like_pipe(node: Optional[ast.AST]) -> bool:
    if node is None:
        return False
    s = expr_to_str(node)
    return ("PIPE" in s) or s.endswith(".PIPE")


def build_import_aliases(tree: ast.AST) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                asname = alias.asname or alias.name
                aliases[asname] = name
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            for alias in node.names:
                name = alias.name
                asname = alias.asname or alias.name
                aliases[asname] = f"{node.module}.{name}"
    return aliases


def resolve_call_name(call: ast.Call, aliases: Dict[str, str]) -> str:
    fn = call.func
    if isinstance(fn, ast.Attribute):
        base = fn.value
        if isinstance(base, ast.Name) and base.id in aliases:
            resolved_base = aliases[base.id]
            return f"{resolved_base}.{fn.attr}"
        return f"{expr_to_str(base)}.{fn.attr}"
    if isinstance(fn, ast.Name):
        return aliases.get(fn.id, fn.id)
    return expr_to_str(fn)


SUBPROCESS_FUNCS = {
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_output",
    "subprocess.check_call",
}
OS_FUNCS = {"os.system", "os.popen"}


def scan_python(path: Path, text: str) -> List[Finding]:
    findings: List[Finding] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return findings

    aliases = build_import_aliases(tree)
    lines = text.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = resolve_call_name(node, aliases)
        lineno = getattr(node, "lineno", 1)
        snippet = lines[lineno - 1].strip() if 1 <= lineno <= len(lines) else call_name

        if call_name in SUBPROCESS_FUNCS:
            stdout_node = kw_value_node(node, "stdout")
            stderr_node = kw_value_node(node, "stderr")
            capture_output_node = kw_value_node(node, "capture_output")

            silent = looks_like_devnull(stdout_node) or looks_like_devnull(stderr_node)
            captured = (
                looks_like_pipe(stdout_node)
                or looks_like_pipe(stderr_node)
                or is_true_const(capture_output_node)
            )

            norm_path = str(path).replace("\\", "/")

            # Allowlist: Mimic3 TTS WAV capture (stdout=PIPE es intencional en este módulo)
            if captured and "external/nodo-de-voz-modular-de-lucy/tts.py" in norm_path:
                continue

            # Allowlist (downgrade): wrapper SearXNG JSON helper.
            # En voice_actions se captura stdout/stderr de searxng_query.py para evitar ruido,
            # pero la trazabilidad de la búsqueda queda en el JSON (--json-out) y el "spoken" final.
            allowlisted_capture = False
            if captured and norm_path.endswith("lucy_agents/voice_actions.py"):
                lo = max(0, lineno - 1 - 40)
                hi = min(len(lines), lineno - 1 + 40)
                if any("searxng_query.py" in lines[i] for i in range(lo, hi)):
                    allowlisted_capture = True

            if silent:
                risk = "ALTA"
                detail = (
                    "Salida redirigida a DEVNULL/devnull: se pierden logs "
                    "(ideal: loguear stdout/stderr)."
                )
            elif captured and allowlisted_capture:
                risk = "BAJA"
                detail = (
                    "Salida capturada (PIPE/capture_output) allowlisted: wrapper SearXNG "
                    "usa JSON (--json-out) para trazabilidad y evita ruido en stdout/stderr."
                )
            elif captured:
                risk = "MEDIA"
                detail = (
                    "Salida capturada (PIPE/capture_output): revisá que se imprima "
                    "o se escriba a logs."
                )
            else:
                risk = "BAJA"
                detail = "No parece silenciar salida (hereda stdout/stderr)."

            findings.append(
                Finding(str(path), lineno, f"python:{call_name}", risk, snippet, detail)
            )

        elif call_name in OS_FUNCS:
            findings.append(
                Finding(
                    str(path),
                    lineno,
                    f"python:{call_name}",
                    "MEDIA",
                    snippet,
                    "Llamada shell directa (os.system/os.popen): difícil de trazar/asegurar. "
                    "Ideal: subprocess + logging estándar.",
                )
            )

    return findings


def scan_shell_like(path: Path, text: str) -> List[Finding]:
    findings: List[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if NULL_REDIRECT_RE.search(line):
            stripped = line.strip()
            suppress_stdout = (
                "&>" in stripped
                or ">/dev/null" in stripped
                or "> /dev/null" in stripped
                or "1>/dev/null" in stripped
                or "1> /dev/null" in stripped
            )
            suppress_stderr = (
                "&>" in stripped or "2>/dev/null" in stripped or "2> /dev/null" in stripped
            )

            risk = "ALTA"
            detail = "Redirección a /dev/null: se pierden logs. Ideal: dejar salida o redirigir a archivo de log."

            # Casos comunes y normalmente aceptables (ruido bajo para trazabilidad).
            if re.search(r"\b(command\s+-v|type\s+-P|hash)\b", stripped):
                risk = "BAJA"
                detail = "Redirección a /dev/null en chequeo de existencia de comando (ruido bajo)."
            elif re.search(r"\bgit\s+rev-parse\b", stripped) and "2>/dev/null" in stripped:
                risk = "BAJA"
                detail = "Se oculta stderr de git (fallback esperado cuando no es un repo)."
            elif "cd" in stripped and "&>" in stripped and "pwd" in stripped:
                risk = "BAJA"
                detail = "Se suprime salida de navegación (patrón común para resolver rutas)."
            elif suppress_stderr and not suppress_stdout:
                risk = "MEDIA"
                detail = "Se suprime stderr: revisá si puede ocultar fallos importantes."
            elif suppress_stdout and not suppress_stderr:
                risk = "MEDIA"
                detail = "Se suprime stdout: revisá si esa salida sería útil para trazabilidad."

            findings.append(
                Finding(
                    str(path),
                    i,
                    "shell:redirection",
                    risk,
                    stripped,
                    detail,
                )
            )
    return findings


def scan_js_ts(path: Path, text: str) -> List[Finding]:
    findings: List[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        l = line.strip()
        if ("child_process" in l or "spawn(" in l or "exec(" in l or "execSync(" in l) and (
            "stdio" in l or "ignore" in l
        ):
            risk = "MEDIA" if "ignore" not in l else "ALTA"
            findings.append(
                Finding(
                    str(path),
                    i,
                    "js:child_process",
                    risk,
                    l,
                    "Posible supresión/captura de salida en procesos. Revisar stdio/logging.",
                )
            )
    return findings


def iter_files(roots: List[Path]) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix in TARGET_EXTS:
                out.append(root)
            continue

        if not root.exists():
            continue

        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in TARGET_EXTS:
                continue
            if set(p.parts) & SKIP_DIRS:
                continue
            out.append(p)
    return out


def write_markdown(
    md_path: Path, roots: List[str], files_scanned: int, findings: List[Finding]
) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}
    for f in findings:
        counts[f.risk] = counts.get(f.risk, 0) + 1

    findings_sorted = sorted(
        findings,
        key=lambda x: ({"ALTA": 0, "MEDIA": 1, "BAJA": 2}.get(x.risk, 9), x.file, x.line),
    )

    lines: List[str] = []
    lines.append("# Auditoría de trazabilidad (Lucy)\n\n")
    lines.append(f"- Fecha: {now}\n")
    lines.append(f"- Roots: {', '.join(roots)}\n")
    lines.append(f"- Archivos escaneados: **{files_scanned}**\n")
    lines.append(
        f"- Hallazgos: **ALTA={counts['ALTA']}**, **MEDIA={counts['MEDIA']}**, **BAJA={counts['BAJA']}**\n"
    )

    lines.append("\n## Hallazgos críticos (ALTA)\n\n")
    altas = [f for f in findings_sorted if f.risk == "ALTA"]
    if not altas:
        lines.append("_No se detectaron silenciamientos evidentes a nivel heurístico._\n")
    else:
        for f in altas:
            lines.append(f"- `{f.file}:{f.line}` **{f.kind}** — {f.detail}\n  - `{f.snippet}`\n")

    lines.append("\n## Hallazgos a revisar (MEDIA)\n\n")
    medias = [f for f in findings_sorted if f.risk == "MEDIA"]
    if not medias:
        lines.append("_Nada para revisar en media según heurística._\n")
    else:
        for f in medias:
            lines.append(f"- `{f.file}:{f.line}` **{f.kind}** — {f.detail}\n  - `{f.snippet}`\n")

    lines.append("\n## Hallazgos informativos (BAJA)\n\n")
    bajas = [f for f in findings_sorted if f.risk == "BAJA"]
    if not bajas:
        lines.append("_Sin entradas de baja._\n")
    else:
        for f in bajas[:120]:
            lines.append(f"- `{f.file}:{f.line}` **{f.kind}**\n  - `{f.snippet}`\n")
        if len(bajas) > 120:
            lines.append(f"\n_(Mostrando 120 de {len(bajas)} de baja.)_\n")

    lines.append("\n## Recomendación mínima para el próximo paso\n\n")
    lines.append(
        "1) Elegir **1 solo** punto de ejecución de comandos (bridge) y estandarizar:\n"
        "- log de inicio/fin\n"
        "- comando exacto\n"
        "- exit_code\n"
        "- stdout/stderr (si se capturan)\n"
        "2) Repetir en el resto.\n"
    )

    new_text = "".join(lines)

    def strip_date_line(text: str) -> str:
        return re.sub(r"^\s*-\s*Fecha:\s*.*\n", "", text, flags=re.M)

    try:
        old_text = md_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        old_text = None

    if old_text is not None and strip_date_line(old_text) == strip_date_line(new_text):
        return

    md_path.write_text(new_text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--roots",
        nargs="+",
        default=["scripts", "lucy_agents", "external/nodo-de-voz-modular-de-lucy"],
        help="Carpetas/archivos a escanear.",
    )
    ap.add_argument("--out-md", default="docs/AUDIT_TRAZABILIDAD.md")
    ap.add_argument("--out-json", default="reports/audit_trazabilidad.json")
    args = ap.parse_args()

    roots = [Path(r) for r in args.roots]
    files = iter_files(roots)

    findings: List[Finding] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if f.suffix == ".py":
            findings.extend(scan_python(f, text))
        elif f.suffix in {".sh", ".bash", ".zsh"}:
            findings.extend(scan_shell_like(f, text))
        elif f.suffix in {".js", ".ts"}:
            findings.extend(scan_js_ts(f, text))

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps([asdict(x) for x in findings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    out_md = Path(args.out_md)
    write_markdown(out_md, args.roots, len(files), findings)

    print(f"[audit_trazabilidad] OK -> {out_md}")
    print(f"[audit_trazabilidad] JSON -> {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
