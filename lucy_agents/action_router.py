#!/usr/bin/env python3
"""Simple action router for Lucy."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

from lucy_agents.chatgpt_bridge import ask_raw
from lucy_agents.chatgpt_client import request as chatgpt_service_request


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _chatgpt_action(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return {"ok": False, "error": "missing prompt", "meta": {"path": "LOCAL"}}

    ask_timeout = _env_int("LUCY_CHATGPT_ASK_TIMEOUT", 75)
    if ask_timeout <= 0:
        ask_timeout = 75
    ask_retries = _env_int("LUCY_CHATGPT_RETRIES", 2)
    if ask_retries < 0:
        ask_retries = 0
    service_timeout = _env_int("LUCY_CHATGPT_SERVICE_TIMEOUT_SEC", 220)
    if service_timeout <= 0:
        service_timeout = 220

    use_service = _env_bool("LUCY_CHATGPT_USE_SERVICE", True)
    if use_service:
        service_resp = chatgpt_service_request(
            prompt,
            timeout_sec=ask_timeout,
            retries=ask_retries,
            wait_sec=service_timeout,
        )
        service_answer = (service_resp.get("answer_text") or "").strip()
        if service_resp.get("ok") and service_answer:
            print("CHATGPT_PATH=SERVICE", file=sys.stderr, flush=True)
            return {
                "ok": True,
                "result": {
                    "answer_text": service_answer,
                    "answer_line": service_resp.get("answer_line") or "",
                },
                "meta": {
                    "path": "SERVICE",
                    "forensics_dir": service_resp.get("forensics_dir"),
                    "elapsed_ms": service_resp.get("elapsed_ms"),
                },
            }
        reason = (service_resp.get("error") or "service_failed").strip() or "service_failed"
        print(
            f"CHATGPT_PATH=DIRECT_FALLBACK reason={reason}",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            "CHATGPT_PATH=DIRECT_FALLBACK reason=SERVICE_DISABLED",
            file=sys.stderr,
            flush=True,
        )

    try:
        result = ask_raw(prompt, timeout_sec=ask_timeout, retries=ask_retries)
    except RuntimeError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "meta": {"path": "DIRECT_FALLBACK"},
        }

    answer_text = (result.get("answer_text") or "").strip()
    if not answer_text:
        return {
            "ok": False,
            "error": "empty answer_text",
            "meta": {"path": "DIRECT_FALLBACK"},
        }

    return {
        "ok": True,
        "result": {
            "answer_text": answer_text,
            "answer_line": result.get("answer_line") or "",
        },
        "meta": {
            "path": "DIRECT_FALLBACK",
            "forensics_dir": result.get("forensics_dir"),
            "elapsed_ms": result.get("elapsed_ms"),
        },
    }


def run_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    if action == "echo":
        return {"ok": True, "result": payload, "meta": {"path": "LOCAL"}}
    if action == "chatgpt_ask":
        return _chatgpt_action(payload)
    return {"ok": False, "error": f"unknown action: {action}", "meta": {"path": "LOCAL"}}


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lucy action router")
    parser.add_argument("action", help="Action name")
    parser.add_argument("payload", help="JSON payload for the action")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        error = {"ok": False, "error": f"invalid json payload: {exc}", "meta": {"path": "LOCAL"}}
        print(json.dumps(error, ensure_ascii=False, separators=(",", ":")))
        print(str(exc), file=sys.stderr, flush=True)
        return 2

    result = run_action(args.action, payload if isinstance(payload, dict) else {"value": payload})
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
