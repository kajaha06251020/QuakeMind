"""WebSocket クライアントのユニットテスト。"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.jma_client import _parse_p2p_event
from app.domain.models import EarthquakeEvent


def _make_ws_message(event_id="test-001", magnitude=5.5, latitude=35.6, longitude=139.7, code=551):
    return json.dumps({
        "code": code,
        "id": event_id,
        "time": "2026/03/25 12:00:00",
        "earthquake": {
            "hypocenter": {
                "magnitude": magnitude,
                "latitude": latitude,
                "longitude": longitude,
                "depth": 20,
                "name": "東京湾",
            }
        }
    })


def test_parse_code_551_returns_event():
    """code=551 のメッセージはパースされる。"""
    raw = json.loads(_make_ws_message())
    event = _parse_p2p_event(raw)
    assert event is not None
    assert isinstance(event, EarthquakeEvent)
    assert event.magnitude == 5.5


def test_parse_missing_latitude_returns_none():
    """latitude が 0.0 のイベントは None を返す。"""
    raw = json.loads(_make_ws_message(latitude=0.0))
    event = _parse_p2p_event(raw)
    assert event is None


def test_parse_negative_magnitude_returns_none():
    """magnitude < 0 のイベントは None を返す。"""
    raw = json.loads(_make_ws_message(magnitude=-1.0))
    event = _parse_p2p_event(raw)
    assert event is None


@pytest.mark.asyncio
async def test_stream_events_yields_valid_events():
    """stream_events() が code=551 のメッセージから EarthquakeEvent を yield する。"""
    from app.infrastructure.jma_client import stream_events

    msg1 = _make_ws_message(event_id="ws-001", magnitude=5.5, code=551)
    msg2 = _make_ws_message(event_id="ws-002", magnitude=4.0, code=999)  # 非551 → スキップ
    msg3 = _make_ws_message(event_id="ws-003", magnitude=6.0, code=551)

    async def _async_iter(items):
        for item in items:
            yield item

    mock_ws = AsyncMock()
    mock_ws.__aiter__ = MagicMock(return_value=_async_iter([msg1, msg2, msg3]))
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=None)

    collected = []
    with patch("app.infrastructure.jma_client.websockets.connect", return_value=mock_ws):
        with patch("app.infrastructure.jma_client.settings") as mock_settings:
            mock_settings.p2p_ws_url = "wss://api.p2pquake.net/v2/ws"
            mock_settings.p2p_ws_reconnect_delay = 1
            gen = stream_events()
            try:
                async for event in gen:
                    collected.append(event)
                    if len(collected) >= 2:
                        await gen.aclose()
                        break
            except StopAsyncIteration:
                pass

    assert len(collected) == 2
    assert collected[0].event_id == "ws-001"
    assert collected[1].event_id == "ws-003"


@pytest.mark.asyncio
async def test_stream_events_reconnects_on_error():
    """stream_events() は接続エラー後に再接続を試みる。"""
    import websockets as ws_lib
    from app.infrastructure.jma_client import stream_events

    call_count = 0

    async def connect_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ws_lib.exceptions.ConnectionClosed(None, None)
        raise asyncio.CancelledError()

    with patch("app.infrastructure.jma_client.websockets.connect", side_effect=connect_side_effect):
        with patch("app.infrastructure.jma_client.settings") as mock_settings:
            mock_settings.p2p_ws_url = "wss://api.p2pquake.net/v2/ws"
            mock_settings.p2p_ws_reconnect_delay = 0
            with patch("app.infrastructure.jma_client.asyncio.sleep", AsyncMock()):
                gen = stream_events()
                with pytest.raises(asyncio.CancelledError):
                    async for _ in gen:
                        pass

    assert call_count == 2
