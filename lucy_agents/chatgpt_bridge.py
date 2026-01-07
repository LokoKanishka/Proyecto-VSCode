#!/usr/bin/env python3
"""
Lucy ChatGPT Bridge (Python API).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from lucy_agents.forensics_summary import summarize_forensics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASK_SCRIPT = PROJECT_ROOT / "scripts" / "lucy_chatgpt_ask.sh"


def _parse_answer_line(stdout: str) -> Optional[str]:
    for line in stdout.splitlines():
        if line.startswith("ANSWER_LINE="):
            return line[len("ANSWER_LINE=") :]
    return None


def _parse_meta(stderr: str) -> tuple[Optional[str], Optional[int]]:
    forensics_dir: Optional[str] = None
    elapsed_ms: Optional[int] = None
    for line in stderr.splitlines():
        if line.startswith("FORENSICS_DIR="):
            forensics_dir = line.split("=", 1)[1].strip()
        elif line.startswith("ELAPSED_MS="):
            raw = line.split("=", 1)[1].strip()
            try:
                elapsed_ms = int(raw)
            except ValueError:
                elapsed_ms = None
    return forensics_dir, elapsed_ms


def _extract_answer_text(answer_line: str) -> str:
    if ": " in answer_line:
        return answer_line.split(": ", 1)[1]
    return answer_line


def _write_summary(forensics_dir: str) -> tuple[bool, Optional[str]]:
    try:
        base = Path(forensics_dir)
        if not base.is_dir():
            return False, None
        summary = summarize_forensics(forensics_dir)
        out_path = base / "summary.json"
        out_path.write_text(
            json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        return True, str(out_path)
    except Exception:  # noqa: BLE001
        return False, None


def ask_raw(prompt: str, timeout_sec: int = 180, retries: int = 2) -> dict:
    if not ASK_SCRIPT.exists():
        raise RuntimeError(f"ask script not found: {ASK_SCRIPT}")

    env = os.environ.copy()
    env["LUCY_CHATGPT_TIMEOUT_SEC"] = str(timeout_sec)
    env["LUCY_CHATGPT_RETRIES"] = str(retries)
    if "CHATGPT_WID_HEX" not in env and "LUCY_CHATGPT_WID_HEX" in env:
        env["CHATGPT_WID_HEX"] = env["LUCY_CHATGPT_WID_HEX"]

    completed = subprocess.run(
        [str(ASK_SCRIPT), prompt],
        capture_output=True,
        text=True,
        env=env,
    )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    answer_line = _parse_answer_line(stdout)
    forensics_dir, elapsed_ms = _parse_meta(stderr)
    summary_written = False
    summary_path: Optional[str] = None
    if forensics_dir:
        summary_written, summary_path = _write_summary(forensics_dir)

    if completed.returncode != 0 or not answer_line:
        message = "chatgpt bridge failed"
        details: list[str] = []
        if completed.returncode != 0:
            details.append(f"rc={completed.returncode}")
        if not answer_line:
            details.append("missing ANSWER_LINE")
        if forensics_dir:
            details.append(f"forensics={forensics_dir}")
        if details:
            message += " (" + ", ".join(details) + ")"
        raise RuntimeError(message)

    answer_text = _extract_answer_text(answer_line)

    return {
        "answer_line": answer_line,
        "answer_text": answer_text,
        "forensics_dir": forensics_dir,
        "elapsed_ms": elapsed_ms,
        "summary_written": summary_written,
        "summary_path": summary_path,
    }


def ask(prompt: str, timeout_sec: int = 180, retries: int = 2) -> str:
    return ask_raw(prompt, timeout_sec=timeout_sec, retries=retries)["answer_text"]


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lucy ChatGPT Bridge (Python API)",
    )
    parser.add_argument("prompt", help="Prompt to send to the ChatGPT bridge")
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=180,
        help="Timeout in seconds (default: 180)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retries for the underlying bridge (default: 2)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        result = ask_raw(args.prompt, timeout_sec=args.timeout_sec, retries=args.retries)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1

    answer_text = result.get("answer_text", "")
    print(answer_text, flush=True)

    forensics_dir = result.get("forensics_dir")
    if forensics_dir:
        print(f"FORENSICS_DIR={forensics_dir}", file=sys.stderr, flush=True)
        if result.get("summary_written"):
            summary_path = result.get("summary_path") or ""
            print(f"SUMMARY_JSON=1 path={summary_path}", file=sys.stderr, flush=True)

    elapsed_ms = result.get("elapsed_ms")
    if elapsed_ms is not None:
        print(f"ELAPSED_MS={elapsed_ms}", file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
