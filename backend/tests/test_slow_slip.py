import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.slow_slip import detect_slow_slip_correlation

def _events(n=60, days=60):
    import random; random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"ss-{i}", magnitude=3.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=random.uniform(0, days))).isoformat()) for i in range(n)]

def test_detect():
    result = detect_slow_slip_correlation(_events())
    assert "slow_slip_candidates" in result
    assert result["observation_days"] > 0

def test_insufficient():
    result = detect_slow_slip_correlation(_events(5))
    assert "error" in result
