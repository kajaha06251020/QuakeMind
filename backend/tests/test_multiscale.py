import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.multiscale import multiscale_analysis

def _events(n=50, days=90):
    import random; random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"ms-{i}", magnitude=round(random.uniform(2, 6), 1), latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=random.uniform(0, days))).isoformat()) for i in range(n)]

def test_multiscale():
    result = multiscale_analysis(_events())
    assert "scales" in result
    assert "daily" in result["scales"]
    assert result["temporal_pattern"] in ("quasi_periodic", "poisson_like", "clustered")

def test_insufficient():
    result = multiscale_analysis(_events(3))
    assert "error" in result
