#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sqlite3
from typing import List

import websockets


def load_events(db_path: str, types: List[str], limit: int) -> List[dict]:
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if types:
        placeholders = ",".join("?" for _ in types)
        query = f"SELECT type, details, timestamp FROM events WHERE type IN ({placeholders}) ORDER BY timestamp ASC"
        if limit:
            query += " LIMIT ?"
            cursor.execute(query, (*types, limit))
        else:
            cursor.execute(query, tuple(types))
    else:
        query = "SELECT type, details, timestamp FROM events ORDER BY timestamp ASC"
        if limit:
            query += " LIMIT ?"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    events = []
    for evt_type, details, ts in rows:
        try:
            payload = json.loads(details) if details else {}
        except Exception:
            payload = {}
        events.append({"type": evt_type, "details": payload, "timestamp": ts})
    return events


async def replay(url: str, events: List[dict], token: str | None, interval: float) -> None:
    async with websockets.connect(url) as ws:
        for evt in events:
            message = {
                "sender": "event_replay",
                "receiver": "broadcast",
                "type": "event",
                "content": evt["type"],
                "data": evt.get("details") or {},
            }
            payload = {"action": "publish", "message": message}
            if token:
                payload["token"] = token
            await ws.send(json.dumps(payload))
            await ws.recv()
            if interval:
                await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay events from sqlite to WS gateway")
    parser.add_argument("--db", default="lucy_memory.db")
    parser.add_argument("--url", default=os.getenv("LUCY_WS_GATEWAY_URL", "ws://127.0.0.1:8766"))
    parser.add_argument("--type", dest="types", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--interval", type=float, default=0.05)
    parser.add_argument("--token", default=os.getenv("LUCY_WS_BRIDGE_TOKEN"))
    args = parser.parse_args()

    events = load_events(args.db, args.types, args.limit)
    if not events:
        print("No hay eventos para replay.")
        return
    asyncio.run(replay(args.url, events, args.token, args.interval))
    print(f"Replay OK: {len(events)} eventos")


if __name__ == "__main__":
    main()
