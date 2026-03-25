"""NASA GUARDIAN クライアントのユニットテスト。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


MOCK_GUARDIAN_RESPONSE = {
    "anomalies": [
        {
            "region": "Japan",
            "latitude": 35.7,
            "longitude": 139.7,
            "anomaly_score": 0.72,
            "observed_at": "2026-03-25T11:00:00Z",
        }
    ]
}


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_disabled():
    """guardian_enabled=False のとき空リストを返す。"""
    from app.infrastructure.guardian_client import fetch_tec_anomalies

    with patch("app.infrastructure.guardian_client.settings") as mock_settings:
        mock_settings.guardian_enabled = False
        result = await fetch_tec_anomalies()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_parses_response():
    """正常レスポンスから TecAnomaly リストを返す。"""
    from app.infrastructure.guardian_client import fetch_tec_anomalies, TecAnomaly

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=MOCK_GUARDIAN_RESPONSE)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.infrastructure.guardian_client.httpx.AsyncClient", return_value=mock_client):
        with patch("app.infrastructure.guardian_client.settings") as mock_settings:
            mock_settings.guardian_enabled = True
            mock_settings.guardian_api_url = "https://guardian.example.com/api/anomalies"
            mock_settings.jma_timeout = 10.0
            result = await fetch_tec_anomalies()

    assert len(result) == 1
    assert isinstance(result[0], TecAnomaly)
    assert result[0].anomaly_score == 0.72
    assert result[0].region == "Japan"


@pytest.mark.asyncio
async def test_fetch_returns_empty_on_http_error():
    """HTTP エラー時は空リストを返す。"""
    import httpx
    from app.infrastructure.guardian_client import fetch_tec_anomalies

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("connection refused"))

    with patch("app.infrastructure.guardian_client.httpx.AsyncClient", return_value=mock_client):
        with patch("app.infrastructure.guardian_client.settings") as mock_settings:
            mock_settings.guardian_enabled = True
            mock_settings.guardian_api_url = "https://guardian.example.com/api/anomalies"
            mock_settings.jma_timeout = 10.0
            result = await fetch_tec_anomalies()

    assert result == []
