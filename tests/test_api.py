"""E2E tests for FastAPI endpoints (requires running server or test client)."""
import pytest
from unittest.mock import AsyncMock, patch

# FastAPI TestClient は同期テスト、httpx.AsyncClient は非同期テスト
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """テスト用 DB を一時ディレクトリに向けて TestClient を返す。"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    # Monitor ループを無効化してテストを高速化
    with patch("api.monitor_loop", new_callable=AsyncMock):
        from api import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_status_returns_200(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "data_stale" in data
    assert "total_alerts" in data


def test_alert_latest_404_when_empty(client):
    resp = client.get("/alert/latest")
    assert resp.status_code == 404


def test_trigger_requires_api_key(client):
    resp = client.post("/trigger", json={})
    assert resp.status_code == 403


def test_trigger_with_valid_key(client):
    resp = client.post(
        "/trigger",
        json={"test_mode": True},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "triggered"
    assert "trigger_id" in data


def test_trigger_magnitude_override_out_of_range(client):
    resp = client.post(
        "/trigger",
        json={"magnitude_override": 15.0},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 422
