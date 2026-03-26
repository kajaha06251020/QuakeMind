import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.criticality import compute_criticality_index

def _events(n=50):
    import random; random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"cr-{i}", magnitude=round(random.uniform(2, 6), 1), latitude=35+random.uniform(-1,1), longitude=139+random.uniform(-1,1), depth_km=10.0, timestamp=(base + timedelta(days=random.uniform(0, 90))).isoformat()) for i in range(n)]

def test_criticality():
    result = compute_criticality_index(_events())
    assert 0 <= result["criticality_index"] <= 1
    assert result["state"] in ("subcritical", "approaching_critical", "near_critical")
    assert "components" in result

def test_insufficient():
    result = compute_criticality_index(_events(5))
    assert "error" in result
