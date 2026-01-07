#!/usr/bin/env python3
"""Diagnostics CLI for Lucy forensics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from lucy_agents.forensics_summary import summarize_forensics


def _load_summary(dir_path: Path) -> dict[str, Any]:
    summary_path = dir_path / "summary.json"
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return summarize_forensics(str(dir_path))


def _render_human(summary: dict[str, Any]) -> str:
    dir_path = summary.get("dir", "-")
    signal = summary.get("signal") or "UNKNOWN"
    elapsed_ms = summary.get("elapsed_ms")
    elapsed_str = str(elapsed_ms) if isinstance(elapsed_ms, int) else "-"
    answer_line = summary.get("answer_line") or "-"
    steps = summary.get("watchdog_steps") or []
    steps_str = ", ".join(steps) if steps else "-"
    copy_bytes = summary.get("copy_bytes")
    copy_bytes_str = str(copy_bytes) if isinstance(copy_bytes, int) else "-"
    copy_chosen = summary.get("copy_chosen") or "-"
    stderr_tail = summary.get("stderr_tail") or ""
    tail_lines = stderr_tail.splitlines() if stderr_tail else []
    if len(tail_lines) > 10:
        tail_lines = tail_lines[-10:]
    tail_block = "\n".join(f"  {line}" for line in tail_lines) if tail_lines else "  -"

    lines = [
        f"Forensics: {dir_path}",
        f"Signal: {signal}",
        f"Elapsed: {elapsed_str}",
        f"AnswerLine: {answer_line}",
        f"Watchdog: {steps_str}",
        f"Copy: bytes={copy_bytes_str} chosen={copy_chosen}",
        "StderrTail:",
        tail_block,
    ]
    return "\n".join(lines)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lucy diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    forense = sub.add_parser("forense", help="Summarize a forensics directory")
    forense.add_argument("dir", help="Path to FORENSICS_DIR")
    forense.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    if args.command != "forense":
        print("ERROR: unknown command", file=sys.stderr)
        return 2

    dir_path = Path(args.dir)
    if not dir_path.exists():
        print(f"ERROR: missing dir: {dir_path}", file=sys.stderr)
        return 2

    summary = _load_summary(dir_path)
    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
        return 0

    print(_render_human(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
