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
from lucy_agents.daily_plan import build_chatgpt_prompt, get_base_plan
from lucy_agents.forensics_summary import summarize_forensics
from lucy_agents.searxng_client import search as searxng_search

ACTION_SPECS: dict[str, dict[str, Any]] = {
    "chatgpt_ask": {
        "payload": {"required": ["prompt"], "optional": ["timeout_sec", "use_service"]},
        "returns": {"answer_text": "str", "answer_line": "str|None"},
        "path": "SERVICE|DIRECT_FALLBACK",
        "notes": "uses ChatGPT UI bridge",
    },
    "daily_plan": {
        "payload": {
            "required": [],
            "optional": ["date", "use_chatgpt", "prompt_hint", "max_chars"],
        },
        "returns": {
            "base_plan": "str",
            "final_plan": "str",
            "source": "FILE|OFFLINE",
            "chatgpt_used": "bool",
            "chatgpt_path": "SERVICE|DIRECT_FALLBACK|NONE|FAILED",
        },
        "path": "LOCAL|SERVICE|DIRECT_FALLBACK",
        "notes": "local-first plan, optional ChatGPT enhancement",
    },
    "echo": {
        "payload": {"required": [], "optional": ["..."]},
        "returns": "payload passthrough",
        "path": "LOCAL",
        "notes": "sanity/offline",
    },
    "summarize_forense": {
        "payload": {"required": ["dir"], "optional": []},
        "returns": "forensics summary dict",
        "path": "LOCAL",
        "notes": "offline parser",
    },
    "web_search": {
        "payload": {"required": ["query"], "optional": ["num_results", "language", "safesearch", "time_range"]},
        "returns": {
            "query": "str",
            "engine": "searxng",
            "searxng_url": "str",
            "results": "list[{title,url,snippet,engine}]",
            "errors": "list[str]",
        },
        "path": "LOCAL",
        "notes": "local searxng search (no LLM)",
    },
}


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


def _payload_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    if key not in payload:
        return default
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _payload_int(payload: dict[str, Any], key: str, default: int) -> int:
    if key not in payload:
        return default
    value = payload.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _chatgpt_action(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return {"ok": False, "error": "missing prompt", "meta": {"path": "LOCAL"}}

    ask_timeout = _payload_int(payload, "timeout_sec", _env_int("LUCY_CHATGPT_ASK_TIMEOUT", 75))
    if ask_timeout <= 0:
        ask_timeout = 75
    ask_retries = _env_int("LUCY_CHATGPT_RETRIES", 2)
    if ask_retries < 0:
        ask_retries = 0
    service_timeout = _env_int("LUCY_CHATGPT_SERVICE_TIMEOUT_SEC", 220)
    if service_timeout <= 0:
        service_timeout = 220

    use_service = _payload_bool(payload, "use_service", _env_bool("LUCY_CHATGPT_USE_SERVICE", True))
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


def _daily_plan_action(payload: dict[str, Any]) -> dict[str, Any]:
    date_str = (payload.get("date") or "").strip() if isinstance(payload, dict) else ""
    prompt_hint = (payload.get("prompt_hint") or "").strip() if isinstance(payload, dict) else ""
    max_chars = _payload_int(payload, "max_chars", 2500)
    if max_chars <= 0:
        max_chars = 2500
    use_chatgpt = _payload_bool(payload, "use_chatgpt", False)

    base_plan, source = get_base_plan(date_str or None, max_chars=max_chars)
    final_plan = base_plan
    chatgpt_used = False
    chatgpt_path = "NONE"

    if use_chatgpt:
        chatgpt_used = True
        prompt = build_chatgpt_prompt(base_plan, date_str or None, prompt_hint, max_chars)
        resp = _chatgpt_action({"prompt": prompt})
        if resp.get("ok"):
            answer_text = (resp.get("result", {}).get("answer_text") or "").strip()
            if answer_text:
                final_plan = answer_text[:max_chars]
                chatgpt_path = resp.get("meta", {}).get("path", "UNKNOWN")
            else:
                chatgpt_path = "FAILED"
        else:
            chatgpt_path = resp.get("meta", {}).get("path", "FAILED")

    return {
        "ok": True,
        "result": {
            "base_plan": base_plan,
            "final_plan": final_plan,
            "source": source,
            "chatgpt_used": chatgpt_used,
            "chatgpt_path": chatgpt_path,
        },
        "meta": {"path": chatgpt_path if chatgpt_used else "LOCAL"},
    }


def _web_search_action(payload: dict[str, Any]) -> dict[str, Any]:
    query = (payload.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "missing query", "meta": {"path": "LOCAL"}}

    num_results = _payload_int(payload, "num_results", 5)
    if num_results <= 0:
        num_results = 1
    if num_results > 10:
        num_results = 10

    language = (payload.get("language") or "es").strip() or "es"
    safesearch = _payload_int(payload, "safesearch", 0)

    time_range = payload.get("time_range")
    if isinstance(time_range, str):
        time_range = time_range.strip() or None
    else:
        time_range = None
    if time_range not in {None, "day", "week", "month", "year"}:
        time_range = None

    timeout_sec = _env_float("SEARXNG_TIMEOUT_SEC", 10.0)

    results, errors, searxng_url = searxng_search(
        query,
        num_results=num_results,
        language=language,
        safesearch=safesearch,
        time_range=time_range,
        timeout_sec=timeout_sec,
    )

    return {
        "ok": True if results is not None else False,
        "result": {
            "query": query,
            "engine": "searxng",
            "searxng_url": searxng_url,
            "results": results,
            "errors": errors,
        },
        "meta": {"path": "LOCAL"},
    }


def run_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    if action == "echo":
        return {"ok": True, "result": payload, "meta": {"path": "LOCAL"}}
    if action == "chatgpt_ask":
        return _chatgpt_action(payload)
    if action == "daily_plan":
        return _daily_plan_action(payload)
    if action == "summarize_forense":
        dir_path = payload.get("dir") if isinstance(payload, dict) else None
        if not dir_path:
            return {"ok": False, "error": "missing dir", "meta": {"path": "LOCAL"}}
        summary = summarize_forensics(str(dir_path))
        return {"ok": True, "result": summary, "meta": {"path": "LOCAL"}}
    if action == "web_search":
        return _web_search_action(payload if isinstance(payload, dict) else {})
    return {"ok": False, "error": f"unknown action: {action}", "meta": {"path": "LOCAL"}}


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lucy action router")
    parser.add_argument("--list", action="store_true", dest="list_actions")
    parser.add_argument("--describe", dest="describe_action")
    parser.add_argument("action", nargs="?", help="Action name")
    parser.add_argument("payload", nargs="?", help="JSON payload for the action")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    if args.list_actions:
        for name in sorted(ACTION_SPECS.keys()):
            print(name)
        return 0

    if args.describe_action:
        spec = ACTION_SPECS.get(args.describe_action)
        if not spec:
            print(f"ERROR: unknown action: {args.describe_action}", file=sys.stderr)
            return 2
        print(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
        return 0

    if not args.action or args.payload is None:
        print("ERROR: missing action or payload", file=sys.stderr)
        return 2

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
