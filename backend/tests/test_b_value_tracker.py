"""b値時系列追跡のテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.b_value_tracker import compute_b_value_timeseries


def _make_events(n: int, start_date: datetime, days_span: int = 180) -> list[EarthquakeRecord]:
    import random
    random.seed(42)
    events = []
    for i in range(n):
        t = start_date + timedelta(days=random.uniform(0, days_span))
        events.append(EarthquakeRecord(
            event_id=f"test-{i:04d}",
            magnitude=round(random.uniform(1.5, 6.0), 1),
            latitude=35.0 + random.uniform(-1, 1),
            longitude=139.0 + random.uniform(-1, 1),
            depth_km=random.uniform(5, 100),
            timestamp=t.isoformat(),
        ))
    return events


def test_timeseries_basic():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(100, start)
    result = compute_b_value_timeseries(events, window_days=90, step_days=30)
    assert len(result) > 0
    for entry in result:
        assert "start" in entry
        assert "end" in entry
        assert "b_value" in entry
        assert "a_value" in entry
        assert "n_events" in entry


def test_timeseries_insufficient_data():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(3, start, days_span=10)
    result = compute_b_value_timeseries(events, window_days=90, step_days=30)
    assert result == []


def test_timeseries_window_size():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(200, start, days_span=365)
    result_90 = compute_b_value_timeseries(events, window_days=90, step_days=30)
    result_180 = compute_b_value_timeseries(events, window_days=180, step_days=30)
    assert len(result_90) >= len(result_180)
