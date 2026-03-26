import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.hazard_map import compute_hazard_map


def _events(n=30):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"hm-{i}",
            magnitude=round(random.uniform(2.0, 6.0), 1),
            latitude=35.0 + random.uniform(-3, 3),
            longitude=139.0 + random.uniform(-3, 3),
            depth_km=10.0,
            timestamp=(base + timedelta(days=random.uniform(0, 90))).isoformat(),
        )
        for i in range(n)
    ]


def test_hazard_map_basic():
    result = compute_hazard_map(_events())
    assert len(result["sites"]) > 0
    for s in result["sites"]:
        assert 0 <= s["hazard_score"] <= 100
        assert s["hazard_level"] in ("low", "moderate", "high", "very_high")


def test_hazard_map_insufficient():
    result = compute_hazard_map(_events(3))
    assert "error" in result
