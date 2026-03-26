import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.explainability import explain_prediction

def _events(n=30):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"xai-{i}", magnitude=round(random.uniform(2.0, 6.0), 1),
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp=(base + timedelta(days=i)).isoformat()) for i in range(n)]

def test_explain_basic():
    result = explain_prediction(_events())
    assert "feature_importance" in result
    assert "explanation" in result
    assert sum(result["feature_importance"].values()) > 0.99

def test_explain_insufficient():
    result = explain_prediction(_events(3))
    assert "error" in result
