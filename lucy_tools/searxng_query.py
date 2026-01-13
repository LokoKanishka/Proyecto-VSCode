#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Tuple
from urllib import parse, request


def fetch_json(url: str, timeout: float = 10.0) -> Tuple[dict[str, Any], bytes]:
    req = request.Request(url, headers={"Accept": "application/json"})
    with request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
    return json.loads(data.decode("utf-8", errors="replace")), data


def main() -> int:
    ap = argparse.ArgumentParser(description="Query local SearXNG JSON and print top results.")
    ap.add_argument("query", help="Search query")
    ap.add_argument(
        "--url",
        default=os.environ.get("SEARXNG_URL")
        or os.environ.get("LUCY_SEARXNG_URL")
        or "http://127.0.0.1:8080",
        help="Base URL of SearXNG (default: env SEARXNG_URL/LUCY_SEARXNG_URL or http://127.0.0.1:8080)",
    )
    ap.add_argument("--language", default="es-AR")
    ap.add_argument("--safesearch", type=int, default=1)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--snippets", action="store_true")
    ap.add_argument("--json-out", default="", help="Write raw JSON response to this path")

    args = ap.parse_args()

    base = args.url.rstrip("/")
    params = {
        "q": args.query,
        "format": "json",
        "language": args.language,
        "safesearch": str(args.safesearch),
    }
    full_url = f"{base}/search?{parse.urlencode(params, quote_via=parse.quote)}"

    try:
        payload, raw = fetch_json(full_url, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        print(f"[searxng_query] ERROR: {exc}", file=sys.stderr)
        print(f"[searxng_query] URL: {full_url}", file=sys.stderr)
        return 2

    if args.json_out:
        try:
            with open(args.json_out, "wb") as f:
                f.write(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"[searxng_query] WARN: no pude escribir {args.json_out}: {exc}", file=sys.stderr)

    results = payload.get("results") or []
    q = payload.get("query") or args.query
    print(f"query: {q}")
    print(f"results: {len(results)}")

    for i, r in enumerate(results[: max(0, args.top)], 1):
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        content = " ".join(((r.get("content") or "").split()))
        print(f"{i}. {title}")
        print(f"   {url}")
        if args.snippets and content:
            print(f"   {content[:220]}")

    unresp = payload.get("unresponsive_engines") or []
    if unresp:
        print("[searxng_query] unresponsive_engines:", ", ".join(unresp[:20]), file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
