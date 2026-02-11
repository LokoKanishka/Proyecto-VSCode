#!/usr/bin/env python3
"""Offline forensics summary for ChatGPT bridge requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_elapsed_ms(meta_text: str, stderr_text: str, stdout_text: str) -> int | None:
    for source in (meta_text, stderr_text, stdout_text):
        for line in source.splitlines():
            if line.startswith("ELAPSED_MS="):
                raw = line.split("=", 1)[1].strip()
                try:
                    return int(raw)
                except ValueError:
                    return None
    return None


def _extract_answer_line(stdout_text: str, stderr_text: str) -> str | None:
    for source in (stdout_text, stderr_text):
        for line in source.splitlines():
            if line.startswith("LUCY_ANSWER_"):
                return line.strip()
            if line.startswith("ANSWER_LINE="):
                return line.split("=", 1)[1].strip()
    return None


def _extract_watchdog_steps(stderr_text: str) -> list[str]:
    steps: list[str] = []
    for line in stderr_text.splitlines():
        if line.startswith("WATCHDOG_STEP="):
            value = line.split("=", 1)[1].strip()
            if " " in value:
                value = value.split(" ", 1)[0]
            steps.append(value)
    return steps[:10]


def _extract_copy_metrics(stderr_text: str) -> tuple[int | None, str | None]:
    copy_bytes = None
    copy_chosen = None
    for line in stderr_text.splitlines():
        if "COPY_BYTES=" in line:
            parts = line.split()
            for part in parts:
                if part.startswith("COPY_BYTES="):
                    raw = part.split("=", 1)[1]
                    try:
                        copy_bytes = int(raw)
                    except ValueError:
                        copy_bytes = None
        if "COPY_CHOSEN=" in line:
            parts = line.split()
            for part in parts:
                if part.startswith("COPY_CHOSEN="):
                    copy_chosen = part.split("=", 1)[1]
    return copy_bytes, copy_chosen


def _stderr_tail(stderr_text: str, max_lines: int = 10) -> str:
    lines = stderr_text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def summarize_forensics(dir_path: str) -> dict[str, Any]:
    base = Path(dir_path)
    request_path = base / "request.txt"
    stdout_path = base / "stdout.txt"
    stderr_path = base / "stderr.txt"
    meta_path = base / "meta.env"
    copy_path = base / "copy.txt"

    request_text = _read_text(request_path) if request_path.exists() else ""
    stdout_text = _read_text(stdout_path) if stdout_path.exists() else ""
    stderr_text = _read_text(stderr_path) if stderr_path.exists() else ""
    meta_text = _read_text(meta_path) if meta_path.exists() else ""

    elapsed_ms = _parse_elapsed_ms(meta_text, stderr_text, stdout_text)
    answer_line = _extract_answer_line(stdout_text, stderr_text)
    watchdog_steps = _extract_watchdog_steps(stderr_text)
    stall_detected = "STALL_DETECTED" in stderr_text
    copy_bytes, copy_chosen = _extract_copy_metrics(stderr_text)

    signal = "UNKNOWN"
    if answer_line:
        signal = "OK"
    elif "ERROR" in stderr_text:
        signal = "FAIL"

    return {
        "dir": str(base),
        "has_request": request_path.exists(),
        "has_copy": copy_path.exists(),
        "elapsed_ms": elapsed_ms,
        "answer_line": answer_line,
        "watchdog_steps": watchdog_steps,
        "stall_detected": stall_detected,
        "copy_bytes": copy_bytes,
        "copy_chosen": copy_chosen,
        "stderr_tail": _stderr_tail(stderr_text),
        "signal": signal,
        "request_head": "\n".join(request_text.splitlines()[:5]),
    }
