"""Phase 5: collector tests on SQLite (Postgres cannot run in this VM).

The repository uses plain SQLAlchemy + ILIKE/LIKE, so the same code
paths run against SQLite here and Postgres in Docker Compose.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path}/logs.db")
    app.state.db.create_all()
    return TestClient(app)


def ts(minutes_ago: int = 0) -> str:
    moment = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return moment.isoformat()


def ingest(client, lines) -> None:
    response = client.post("/ingest", json={"lines": lines})
    assert response.status_code == 202
    assert response.json()["accepted"] == len(lines)


def sample_lines() -> list[dict]:
    return [
        {"service": "api", "ts": ts(5), "level": "INFO", "message": "started ok"},
        {"service": "api", "ts": ts(4), "level": "ERROR", "message": "database timeout"},
        {"service": "worker", "ts": ts(3), "level": "ERROR", "message": "job failed"},
        {"service": "api", "ts": ts(60 * 72), "level": "ERROR", "message": "old timeout"},
    ]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_collector_starts_empty(client):
    assert client.get("/logs").json() == []


def test_ingest_then_query_all(client):
    ingest(client, sample_lines())
    rows = client.get("/logs").json()
    assert len(rows) == 4
    assert rows[0]["message"] == "job failed"  # newest first


def test_filter_by_service(client):
    ingest(client, sample_lines())
    rows = client.get("/logs", params={"service": "api"}).json()
    assert len(rows) == 3
    assert all(row["service"] == "api" for row in rows)


def test_filter_by_level_case_insensitive(client):
    ingest(client, sample_lines())
    rows = client.get("/logs", params={"level": "ERROR"}).json()
    assert len(rows) == 3
    assert all(row["level"] == "error" for row in rows)


def test_filter_by_text_search(client):
    ingest(client, sample_lines())
    rows = client.get("/logs", params={"q": "timeout"}).json()
    assert len(rows) == 2
    assert all("timeout" in row["message"] for row in rows)


def test_filter_by_since_excludes_old(client):
    ingest(client, sample_lines())
    rows = client.get("/logs", params={"since": "1h"}).json()
    assert len(rows) == 3
    assert all(row["message"] != "old timeout" for row in rows)


def test_combined_filters(client):
    ingest(client, sample_lines())
    rows = client.get(
        "/logs", params={"service": "api", "level": "error", "q": "timeout", "since": "1h"}
    ).json()
    assert len(rows) == 1
    assert rows[0]["message"] == "database timeout"


def test_invalid_since_is_400(client):
    response = client.get("/logs", params={"since": "yesterday"})
    assert response.status_code == 400
    assert "Invalid since" in response.json()["detail"]


def test_ingest_validation_error_is_422(client):
    response = client.post("/ingest", json={"lines": [{"service": "api"}]})
    assert response.status_code == 422
