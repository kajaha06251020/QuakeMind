"""マルチソースアグリゲーターのユニットテスト。"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.domain.models import EarthquakeEvent

_BASE_TIME = datetime(2026, 3, 25, 12, 0, 0, tzinfo=timezone.utc)


def _make_event(event_id, lat, lon, mag, source, seconds_offset=0):
    return EarthquakeEvent(
        event_id=event_id,
        magnitude=mag,
        depth_km=10.0,
        latitude=lat,
        longitude=lon,
        region="テスト地域",
        timestamp=_BASE_TIME + timedelta(seconds=seconds_offset),
        source=source,
    )


def test_deduplicate_removes_near_identical():
    """ほぼ同一の地震（近い座標・マグニチュード・時刻）は1件に絞られる。"""
    from app.infrastructure.multi_source import _deduplicate

    events = [
        _make_event("p2p-001", 35.6, 139.7, 5.5, "p2p", 0),
        _make_event("usgs-001", 35.61, 139.71, 5.5, "usgs", 30),  # 近い → 重複
    ]
    result = _deduplicate(events)
    assert len(result) == 1
    assert result[0].event_id == "p2p-001"  # P2P 優先


def test_deduplicate_keeps_distant_events():
    """座標が離れたイベントは別イベントとして残す。"""
    from app.infrastructure.multi_source import _deduplicate

    events = [
        _make_event("p2p-001", 35.6, 139.7, 5.5, "p2p", 0),
        _make_event("usgs-002", 38.0, 141.5, 4.8, "usgs", 0),  # 遠い → 別イベント
    ]
    result = _deduplicate(events)
    assert len(result) == 2


def test_deduplicate_keeps_time_separated():
    """時刻が 120 秒以上離れているイベントは別イベントとして残す。"""
    from app.infrastructure.multi_source import _deduplicate

    events = [
        _make_event("p2p-001", 35.6, 139.7, 5.5, "p2p", 0),
        _make_event("usgs-002", 35.6, 139.7, 5.5, "usgs", 200),  # 200秒後 → 別イベント
    ]
    result = _deduplicate(events)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_fetch_all_sources_aggregates():
    """各ソースの結果が集約される。"""
    from app.infrastructure.multi_source import fetch_all_sources

    p2p_event = _make_event("p2p-001", 35.6, 139.7, 5.5, "p2p")
    usgs_event = _make_event("usgs-002", 38.0, 141.5, 4.8, "usgs")

    with patch("app.infrastructure.multi_source.p2p_fetch", AsyncMock(return_value=[p2p_event])):
        with patch("app.infrastructure.multi_source.usgs_fetch", AsyncMock(return_value=[usgs_event])):
            with patch("app.infrastructure.multi_source.jma_xml_fetch", AsyncMock(return_value=[])):
                result = await fetch_all_sources(limit=20)

    assert len(result) == 2
