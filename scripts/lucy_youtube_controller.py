#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from urllib.parse import quote_plus

# CLI wrapper for Guard (A34) + Scan (A35).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_GUARD = os.path.join(BASE_DIR, "chrome_guard_diego_client.sh")
SCRIPT_SCAN = os.path.join(BASE_DIR, "youtube_doctor_scan.sh")

REQUIRED_PROFILE = "diego"


def _run_guard(url: str) -> bool:
    """Invoke Guard to navigate safely."""
    if not os.path.isfile(SCRIPT_GUARD):
        print(f"ERROR_NO_GUARD: {SCRIPT_GUARD}", file=sys.stderr)
        return False

    env = dict(os.environ)
    env["CHROME_PROFILE_NAME"] = REQUIRED_PROFILE
    proc = subprocess.run([SCRIPT_GUARD, url], stdout=sys.stderr, stderr=sys.stderr, env=env)
    if proc.returncode != 0:
        print(f"ERROR_GUARD_FAILED rc={proc.returncode}", file=sys.stderr)
        return False
    return True


def _run_scan():
    """Invoke scanner and parse JSON list."""
    if not os.path.isfile(SCRIPT_SCAN):
        print(f"ERROR_NO_SCAN: {SCRIPT_SCAN}", file=sys.stderr)
        return []

    proc = subprocess.run([SCRIPT_SCAN], stdout=subprocess.PIPE, stderr=sys.stderr, text=True)
    if proc.returncode != 0:
        print("ERROR_SCAN_FAILED", file=sys.stderr)
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("ERROR_SCAN_INVALID_JSON", file=sys.stderr)
        return []


def action_search(query: str) -> dict:
    """Search YouTube and return a list of videos."""
    encoded_query = quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

    if not _run_guard(search_url):
        return {"status": "error", "message": "guard_failed"}

    videos = _run_scan()
    if not videos:
        return {"status": "empty", "message": "no_results"}

    return {
        "status": "success",
        "action": "search",
        "query": query,
        "results": videos,
    }


def action_play(video_id: str | None = None, url: str | None = None) -> dict:
    """Play a specific video."""
    target_url = url
    if not target_url and video_id:
        target_url = f"https://www.youtube.com/watch?v={video_id}"

    if not target_url:
        return {"status": "error", "message": "missing_video"}

    if _run_guard(target_url):
        return {"status": "success", "action": "play", "url": target_url}
    return {"status": "error", "message": "guard_failed"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lucy YouTube Controller (Guard + Scan wrapper)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_search = subparsers.add_parser("search", help="Search videos")
    parser_search.add_argument("query", type=str, help="Search query")

    parser_play = subparsers.add_parser("play", help="Play a video")
    group = parser_play.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", type=str, help="YouTube video id")
    group.add_argument("--url", type=str, help="Full URL")

    args = parser.parse_args()

    if args.command == "search":
        result = action_search(args.query)
    elif args.command == "play":
        result = action_play(video_id=args.id, url=args.url)
    else:
        result = {"status": "error", "message": "unknown_command"}

    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
