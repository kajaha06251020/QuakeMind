"""Research Mode のテスト。"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.research import generate_research_report


def _make_events(n=20):
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"res-{i}", magnitude=3.0 + i * 0.1,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_research_report_basic():
    with patch("app.usecases.research.LocalLLMProvider") as MockProvider:
        mock = AsyncMock()
        mock.generate_notes.return_value = "テストレポート: 活動は正常範囲です。"
        MockProvider.return_value = mock
        result = await generate_research_report(_make_events(20))
    assert "event_count" in result
    assert result["event_count"] == 20
    assert "magnitude_range" in result


@pytest.mark.asyncio
async def test_research_report_insufficient():
    result = await generate_research_report(_make_events(3))
    assert "error" in result
