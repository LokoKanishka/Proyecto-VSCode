import argparse
import json
from pathlib import Path
from typing import Dict, List


LOG_FILE = Path("logs/resource_events.jsonl")


def load_events(limit: int = 50) -> List[Dict]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8") as fd:
        lines = fd.readlines()[-limit:]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line.strip()))
        except json.JSONDecodeError:
            continue
    return events


def summarize(events: List[Dict]):
    summary = {
        "gpu": None,
        "windows": [],
        "files": [],
        "notifications": [],
        "ticks": [],
    }
    for event in reversed(events):
        name = event.get("event")
        data = event.get("data", {})
        if name == "gpu_pressure" and summary["gpu"] is None:
            summary["gpu"] = data.get("usage_pct")
        elif name == "window_opened" and len(summary["windows"]) < 5:
            summary["windows"].append(data)
        elif name == "file_created" and len(summary["files"]) < 3:
            summary["files"].append(data)
        elif name == "file_modified" and len(summary["files"]) < 3:
            summary["files"].append(data)
        elif name == "notification_received" and len(summary["notifications"]) < 3:
            summary["notifications"].append(data)
        elif name == "timer_tick":
            summary["ticks"].append(data)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Mostrar el estado de recursos de Lucy.")
    parser.add_argument("--limit", type=int, default=50, help="Cantidad de eventos a leer")
    args = parser.parse_args()

    events = load_events(limit=args.limit)
    summary = summarize(events)
    print(f"Último uso de GPU: {summary['gpu']}")
    if summary["windows"]:
        print("Ventanas recientes detectadas:")
        for item in summary["windows"]:
            print(f"  - {item.get('title')} ({item.get('window_id')})")
    if summary["files"]:
        print("Archivos recientes detectados por FileWatcher:")
        for item in summary["files"]:
            print(f"  - {item.get('path')} ({item.get('event')}, {item.get('size')} bytes)")
    if summary["notifications"]:
        print("Notificaciones recientes:")
        for item in summary["notifications"]:
            preview = item.get("strings") or [item.get("note")]
            print(f"  - {preview[0] if preview else 'sin detalle'}")
    if summary["ticks"]:
        print(f"TimerWatcher ticks: {len(summary['ticks'])} (último tick: {summary['ticks'][-1].get('tick')})")


if __name__ == "__main__":
    main()
