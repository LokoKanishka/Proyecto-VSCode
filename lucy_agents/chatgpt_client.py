#!/usr/bin/env python3
"""ChatGPT bridge client using file queue (no sockets)."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = PROJECT_ROOT / "diagnostics" / "chatgpt_queue"
INBOX_DIR = QUEUE_ROOT / "inbox"
OUTBOX_DIR = QUEUE_ROOT / "outbox"
LOGS_DIR = QUEUE_ROOT / "logs"
PROCESSED_DIR = QUEUE_ROOT / "processed"

POLL_SEC = 0.2


def _ensure_dirs() -> None:
    for d in (INBOX_DIR, OUTBOX_DIR, LOGS_DIR, PROCESSED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lucy ChatGPT queue client")
    parser.add_argument("prompt", help="Prompt to send to the ChatGPT service")
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--wait-sec", type=int, default=220)
    return parser.parse_args(argv)


def request(
    prompt: str,
    timeout_sec: int = 180,
    retries: int = 2,
    wait_sec: int = 220,
) -> dict[str, Any]:
    _ensure_dirs()

    prompt = (prompt or "").strip()
    if not prompt:
        return {
            "id": "",
            "ok": False,
            "answer_text": "",
            "answer_line": "",
            "forensics_dir": None,
            "elapsed_ms": None,
            "error": "empty prompt",
        }

    req_id = f"REQ_{int(time.time())}_{random.randint(1000, 99999)}"
    req_payload = {
        "id": req_id,
        "prompt": prompt,
        "timeout_sec": int(timeout_sec),
        "retries": int(retries),
        "created_at": _now_iso(),
    }

    req_path = INBOX_DIR / f"{req_id}.json"
    _write_json(req_path, req_payload)

    resp_path = OUTBOX_DIR / f"RES_{req_id}.json"
    deadline = time.time() + max(int(wait_sec), 1)

    while time.time() < deadline:
        if resp_path.exists():
            try:
                raw = resp_path.read_text(encoding="utf-8")
                resp = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                return {
                    "id": req_id,
                    "ok": False,
                    "answer_text": "",
                    "answer_line": "",
                    "forensics_dir": None,
                    "elapsed_ms": None,
                    "error": f"invalid response json: {exc}",
                }

            resp.setdefault("id", req_id)
            resp.setdefault("answer_text", "")
            resp.setdefault("answer_line", "")
            resp.setdefault("forensics_dir", None)
            resp.setdefault("elapsed_ms", None)
            resp.setdefault("error", "")
            resp["ok"] = bool(resp.get("ok"))
            return resp

        time.sleep(POLL_SEC)

    return {
        "id": req_id,
        "ok": False,
        "answer_text": "",
        "answer_line": "",
        "forensics_dir": None,
        "elapsed_ms": None,
        "error": "response timeout",
    }


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    resp = request(
        args.prompt,
        timeout_sec=int(args.timeout_sec),
        retries=int(args.retries),
        wait_sec=int(args.wait_sec),
    )

    if resp.get("ok") and (resp.get("answer_text") or "").strip():
        print((resp.get("answer_text") or "").strip(), flush=True)
        forensics_dir = resp.get("forensics_dir")
        elapsed_ms = resp.get("elapsed_ms")
        print(f"FORENSICS_DIR={forensics_dir}", file=sys.stderr, flush=True)
        if elapsed_ms is not None:
            print(f"ELAPSED_MS={elapsed_ms}", file=sys.stderr, flush=True)
        return 0

    error = resp.get("error") or "unknown error"
    print(f"ERROR: {error}", file=sys.stderr, flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
