#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser(description="Export events to JSONL for golden traces")
    parser.add_argument("--db", default="lucy_memory.db")
    parser.add_argument("--out", default="logs/event_trace.jsonl")
    parser.add_argument("--type", dest="types", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print("DB not found")
        return

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()
    if args.types:
        placeholders = ",".join("?" for _ in args.types)
        query = f"SELECT type, details, timestamp FROM events WHERE type IN ({placeholders}) ORDER BY timestamp ASC"
        params = list(args.types)
    else:
        query = "SELECT type, details, timestamp FROM events ORDER BY timestamp ASC"
        params = []
    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for evt_type, details, ts in rows:
            try:
                payload = json.loads(details) if details else {}
            except Exception:
                payload = {}
            fh.write(json.dumps({"type": evt_type, "details": payload, "timestamp": ts}) + "\n")
    print(f"Exported {len(rows)} events to {args.out}")


if __name__ == "__main__":
    main()
