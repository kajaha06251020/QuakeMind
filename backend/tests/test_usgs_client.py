"""USGS クライアントのユニットテスト（HTTP モック使用）。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.domain.models import EarthquakeEvent


MOCK_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "properties": {
                "mag": 5.5,
                "place": "10 km E of Tokyo, Japan",
                "time": 1711360000000,
                "ids": ",us2026abc,",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [139.7, 35.6, 20.0],
            },
        },
        {
            "properties": {
                "mag": -1.0,   # 無効データ（フィルタ対象）
                "place": "Unknown",
                "time": 1711360001000,
                "ids": ",us2026bad,",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [0.0, 0.0, 0.0],
            },
        },
    ],
}


@pytest.mark.asyncio
async def test_fetch_returns_valid_events():
    """正常レスポンスから EarthquakeEvent リストを返す。"""
    from app.infrastructure.usgs_client import fetch_recent_events

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=MOCK_GEOJSON)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.infrastructure.usgs_client.httpx.AsyncClient", return_value=mock_client):
        events = await fetch_recent_events(limit=20)

    assert len(events) == 1  # mag=-1 はフィルタされる
    assert isinstance(events[0], EarthquakeEvent)
    assert events[0].magnitude == 5.5
    assert events[0].source == "usgs"


@pytest.mark.asyncio
async def test_fetch_returns_empty_on_http_error():
    """HTTP エラー時は空リストを返す（例外を送出しない）。"""
    import httpx
    from app.infrastructure.usgs_client import fetch_recent_events

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("500"))

    with patch("app.infrastructure.usgs_client.httpx.AsyncClient", return_value=mock_client):
        events = await fetch_recent_events()

    assert events == []


@pytest.mark.asyncio
async def test_fetch_empty_features():
    """features が空のレスポンスは空リストを返す。"""
    from app.infrastructure.usgs_client import fetch_recent_events

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"type": "FeatureCollection", "features": []})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.infrastructure.usgs_client.httpx.AsyncClient", return_value=mock_client):
        events = await fetch_recent_events()

    assert events == []
