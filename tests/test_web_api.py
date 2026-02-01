import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from lucy_web import app as web_app


@pytest.fixture(autouse=True)
def client():
    with web_app.app.test_client() as client:
        yield client


def test_bus_metrics_endpoint_returns_summary(tmp_path, monkeypatch):
    log_file = tmp_path / "bus_metrics.jsonl"
    log_file.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "metrics": {"published": 5}}) + "\n")
    monkeypatch.setattr(web_app, "BUS_METRICS_LOG", log_file)

    resp = web_app.app.test_client().get("/api/bus_metrics")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data
    assert "records" in data


def test_bridge_metrics_endpoint_returns_records(tmp_path, monkeypatch):
    log_file = tmp_path / "bridge_metrics.jsonl"
    log_file.write_text(json.dumps({"timestamp": 1, "sent": 1, "received": 1, "dropped": 0}) + "\n")
    monkeypatch.setattr(web_app, "BRIDGE_METRICS_LOG", log_file)
    resp = web_app.app.test_client().get("/api/bridge_metrics")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["records"]


def test_memory_events_endpoint_handles_lines(tmp_path, monkeypatch):
    log_file = tmp_path / "memory_retrieval.log"
    line = f"{datetime.now().isoformat()} | retrieved_memory #1: 2 items\n"
    log_file.write_text(line)
    monkeypatch.setattr(web_app, "MEMORY_EVENTS_LOG", log_file)

    resp = web_app.app.test_client().get("/api/memory_events")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["events"], "should return the logged line"
    assert "retrieved_memory" in data["events"][0]["details"]


def test_events_endpoint_filters(tmp_path, monkeypatch):
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE events (id TEXT PRIMARY KEY, timestamp REAL, type TEXT, details TEXT, session_id TEXT)"
    )
    cursor.execute(
        "INSERT INTO events VALUES ('1', 1.0, 'bridge_backpressure', '{}', 's')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(web_app, "db_path", db_path)
    resp = web_app.app.test_client().get("/api/events?type=bridge_backpressure")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["events"]
