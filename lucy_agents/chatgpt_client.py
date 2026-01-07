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


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    _ensure_dirs()

    prompt = (args.prompt or "").strip()
    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr, flush=True)
        return 1

    req_id = f"REQ_{int(time.time())}_{random.randint(1000, 99999)}"
    req_payload = {
        "id": req_id,
        "prompt": prompt,
        "timeout_sec": int(args.timeout_sec),
        "retries": int(args.retries),
        "created_at": _now_iso(),
    }

    req_path = INBOX_DIR / f"{req_id}.json"
    _write_json(req_path, req_payload)

    resp_path = OUTBOX_DIR / f"RES_{req_id}.json"
    deadline = time.time() + max(int(args.wait_sec), 1)

    while time.time() < deadline:
        if resp_path.exists():
            try:
                raw = resp_path.read_text(encoding="utf-8")
                resp = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: invalid response json: {exc}", file=sys.stderr, flush=True)
                return 1

            ok = bool(resp.get("ok"))
            answer_text = (resp.get("answer_text") or "").strip()
            if ok and answer_text:
                print(answer_text, flush=True)
                forensics_dir = resp.get("forensics_dir")
                elapsed_ms = resp.get("elapsed_ms")
                print(f"FORENSICS_DIR={forensics_dir}", file=sys.stderr, flush=True)
                if elapsed_ms is not None:
                    print(f"ELAPSED_MS={elapsed_ms}", file=sys.stderr, flush=True)
                return 0

            error = resp.get("error") or "unknown error"
            print(f"ERROR: {error}", file=sys.stderr, flush=True)
            return 2

        time.sleep(POLL_SEC)

    print("ERROR: response timeout", file=sys.stderr, flush=True)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
