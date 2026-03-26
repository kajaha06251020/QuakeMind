import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.briefing import generate_daily_briefing


def _events(n=10):
    base = datetime(2026, 3, 25, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"br-{i}", magnitude=3.0 + i * 0.2,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base - timedelta(hours=i)).isoformat(),
        )
        for i in range(n)
    ]


def test_briefing_basic():
    result = generate_daily_briefing(_events(10), days=1)
    assert result["total_events"] > 0
    assert "summary" in result


def test_briefing_empty():
    result = generate_daily_briefing([], days=1)
    assert result["total_events"] == 0


def test_briefing_highlights():
    # Use small magnitudes (< 5.0) so the injected M5.5 event is the clear max
    base = datetime(2026, 3, 25, tzinfo=timezone.utc)
    events = [
        EarthquakeRecord(
            event_id=f"br-{i}", magnitude=2.0 + i * 0.1,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base - timedelta(hours=i)).isoformat(),
        )
        for i in range(15)
    ]
    events[0] = EarthquakeRecord(
        event_id="big", magnitude=5.5,
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp=events[0].timestamp,
    )
    result = generate_daily_briefing(events, days=1)
    assert any("M5.5" in h for h in result["highlights"])
