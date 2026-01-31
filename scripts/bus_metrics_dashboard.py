#!/usr/bin/env python3
"""Pequeño reporte de métricas del EventBus para monitorear la salud del enjambre."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from statistics import mean

LOG_PATH = Path("logs/bus_metrics.jsonl")


def tail_lines(path: Path, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    lines = deque(maxlen=limit)
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                lines.append(line.strip())
    return list(lines)


def parse_records(lines: list[str]) -> list[dict]:
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def summarize(records: list[dict]) -> dict:
    if not records:
        return {}
    metrics = [rec.get("metrics", {}) for rec in records]
    keys = set().union(*(m.keys() for m in metrics))
    summary = {}
    for key in keys:
        values = [m.get(key, 0) for m in metrics]
        summary[key] = {
            "latest": values[-1],
            "avg": round(mean(values), 2) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
        }
    return summary


def main() -> None:
    lines = tail_lines(LOG_PATH, limit=30)
    records = parse_records(lines)
    if not records:
        print("No hay métricas registradas en", LOG_PATH)
        return

    summary = summarize(records)
    print("Últimas métricas del EventBus:")
    for key, stats in summary.items():
        print(f"  - {key}: última={stats['latest']}  avg={stats['avg']}  min={stats['min']}  max={stats['max']}")

    print("\nHistorial reciente:")
    for rec in records[-5:]:
        ts = rec.get("timestamp", "???")
        metrics = rec.get("metrics", {})
        metrics_str = " ".join(f"{k}={v}" for k, v in metrics.items())
        print(f"{ts} | {metrics_str}")


if __name__ == "__main__":
    main()
