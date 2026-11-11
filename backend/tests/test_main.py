import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_startup_requires_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
        with TestClient(app):
            pass


def test_health_and_metrics_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-only-secret")

    with TestClient(app) as client:
        health = client.get("/health")
        metrics = client.get("/metrics")

    assert health.status_code == 200
    assert health.text == "ok"
    assert metrics.status_code == 200
    assert "python_info" in metrics.text
