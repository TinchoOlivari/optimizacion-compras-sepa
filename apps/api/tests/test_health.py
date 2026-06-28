from unittest.mock import MagicMock, patch

import psycopg
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_conn() -> MagicMock:
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def test_health_db_ok() -> None:
    with patch("app.api.v1.health.psycopg.connect", return_value=_mock_conn()):
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_db_error() -> None:
    with patch(
        "app.api.v1.health.psycopg.connect",
        side_effect=psycopg.OperationalError("connection refused"),
    ):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "error"}
