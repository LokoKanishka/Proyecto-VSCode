#!/usr/bin/env python3
"""ChatGPT bridge service using a file queue (no sockets)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lucy_agents.chatgpt_bridge import ask_raw

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


def _log_request(req_id: str, message: str) -> None:
    log_path = LOGS_DIR / f"{req_id}.log"
    ts = _now_iso()
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def _load_request(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _request_id_from_path(path: Path) -> str:
    name = path.name
    if name.endswith(".json.work"):
        return name[: -len(".json.work")]
    if name.endswith(".json"):
        return name[: -len(".json")]
    return path.stem


def _process_request(req_path: Path) -> bool:
    file_id = _request_id_from_path(req_path)
    _log_request(file_id, f"request_path={req_path.name}")

    try:
        req = _load_request(req_path)
    except Exception as exc:  # noqa: BLE001
        resp = {
            "id": file_id,
            "ok": False,
            "answer_text": "",
            "answer_line": "",
            "forensics_dir": None,
            "elapsed_ms": None,
            "error": f"invalid request json: {exc}",
        }
        _write_json(OUTBOX_DIR / f"RES_{file_id}.json", resp)
        _log_request(file_id, f"error={resp['error']}")
        return False

    prompt = (req.get("prompt") or "").strip()
    timeout_sec = int(req.get("timeout_sec") or 180)
    retries = int(req.get("retries") or 2)

    if not prompt:
        resp = {
            "id": file_id,
            "ok": False,
            "answer_text": "",
            "answer_line": "",
            "forensics_dir": None,
            "elapsed_ms": None,
            "error": "missing prompt",
        }
        _write_json(OUTBOX_DIR / f"RES_{file_id}.json", resp)
        _log_request(file_id, "error=missing prompt")
        return False

    try:
        result = ask_raw(prompt, timeout_sec=timeout_sec, retries=retries)
    except RuntimeError as exc:
        resp = {
            "id": file_id,
            "ok": False,
            "answer_text": "",
            "answer_line": "",
            "forensics_dir": None,
            "elapsed_ms": None,
            "error": str(exc),
        }
        _write_json(OUTBOX_DIR / f"RES_{file_id}.json", resp)
        _log_request(file_id, f"error={resp['error']}")
        return False

    resp = {
        "id": file_id,
        "ok": True,
        "answer_text": result.get("answer_text") or "",
        "answer_line": result.get("answer_line") or "",
        "forensics_dir": result.get("forensics_dir"),
        "elapsed_ms": result.get("elapsed_ms"),
        "error": "",
    }
    _write_json(OUTBOX_DIR / f"RES_{file_id}.json", resp)
    _log_request(file_id, f"ok=1 elapsed_ms={resp['elapsed_ms']}")
    return True


def main() -> int:
    _ensure_dirs()
    print("SERVICE_READY", flush=True)

    while True:
        req_files = sorted(INBOX_DIR.glob("REQ_*.json"))
        if not req_files:
            time.sleep(POLL_SEC)
            continue

        for req_path in req_files:
            work_path = Path(str(req_path) + ".work")
            try:
                req_path.replace(work_path)
            except FileNotFoundError:
                continue
            except OSError:
                continue

            req_id = _request_id_from_path(work_path)
            print(f"SERVICE_REQ id={req_id}", flush=True)
            ok = _process_request(work_path)
            ok_flag = 1 if ok else 0
            print(f"SERVICE_RES id={req_id} ok={ok_flag}", flush=True)

            processed_path = PROCESSED_DIR / req_path.name
            try:
                work_path.replace(processed_path)
            except OSError:
                try:
                    work_path.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
