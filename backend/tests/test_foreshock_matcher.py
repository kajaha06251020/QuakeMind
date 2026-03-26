"""前震パターンマッチングのテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.foreshock_matcher import match_foreshock_pattern


def _make_increasing_events() -> list[EarthquakeRecord]:
    """日ごとに増加するパターン（前震的）。"""
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    events = []
    for d in range(30):
        count = 1 + d // 5  # 徐々に増加
        for i in range(count):
            events.append(EarthquakeRecord(
                event_id=f"inc-{d}-{i}", magnitude=3.0,
                latitude=35.0, longitude=139.0, depth_km=20.0,
                timestamp=(base + timedelta(days=d, hours=i)).isoformat(),
            ))
    return events


def _make_flat_events() -> list[EarthquakeRecord]:
    """均等なパターン（通常活動）。"""
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"flat-{d}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=d)).isoformat(),
        )
        for d in range(30)
    ]


def test_match_returns_required_fields():
    events = _make_increasing_events()
    result = match_foreshock_pattern(events)
    assert "similarity_score" in result
    assert "pattern_type" in result
    assert "alert_level" in result
    assert 0.0 <= result["similarity_score"] <= 1.0


def test_increasing_pattern_higher_score():
    inc = match_foreshock_pattern(_make_increasing_events())
    flat = match_foreshock_pattern(_make_flat_events())
    assert inc["similarity_score"] >= flat["similarity_score"]


def test_empty_events():
    result = match_foreshock_pattern([])
    assert result["similarity_score"] == 0.0
    assert result["alert_level"] == "normal"
