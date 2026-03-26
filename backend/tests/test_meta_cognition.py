"""メタ認知エンジンのテスト。"""
import pytest
from app.services.meta_cognition import self_evaluate
from app.domain.seismology import EarthquakeRecord


def _make_events(n=50):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=3.5 + (i % 3) * 0.5,
            latitude=35.0 + i * 0.01, longitude=135.0 + i * 0.01,
            depth_km=10.0, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_self_evaluate_keys():
    events = _make_events(50)
    result = await self_evaluate(events)
    assert "overall_confidence" in result
    assert "confidence_level" in result
    assert "factors" in result
    assert "weaknesses" in result
    assert "recommendation" in result
    assert result["confidence_level"] in ("high", "medium", "low")


@pytest.mark.asyncio
async def test_self_evaluate_empty():
    result = await self_evaluate([])
    assert "overall_confidence" in result
    assert result["overall_confidence"] >= 0
    assert result["overall_confidence"] <= 1


@pytest.mark.asyncio
async def test_self_evaluate_confidence_range():
    events = _make_events(100)
    result = await self_evaluate(events)
    assert 0.0 <= result["overall_confidence"] <= 1.0
    assert isinstance(result["factors"], list)
    assert len(result["factors"]) > 0
