#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_trace(path: str):
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare event traces")
    parser.add_argument("--golden", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--max", type=int, default=20)
    args = parser.parse_args()

    golden = load_trace(args.golden)
    current = load_trace(args.current)

    diffs = []
    for idx, (g, c) in enumerate(zip(golden, current)):
        if g.get("type") != c.get("type"):
            diffs.append((idx, "type", g.get("type"), c.get("type")))
        if g.get("details") != c.get("details"):
            diffs.append((idx, "details", g.get("details"), c.get("details")))
        if len(diffs) >= args.max:
            break
    if len(golden) != len(current):
        diffs.append(("length", len(golden), len(current), None))

    if not diffs:
        print("OK: traces match")
        return
    print("Differences:")
    for diff in diffs[: args.max]:
        print(diff)


if __name__ == "__main__":
    main()
