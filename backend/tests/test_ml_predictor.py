import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.ml_predictor import predict_large_earthquake, _extract_features

def _events(n=30, base_mag=3.0):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"ml-{i}", magnitude=round(base_mag + random.uniform(-1, 2), 1),
        latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=i)).isoformat()) for i in range(n)]

def test_predict_basic():
    result = predict_large_earthquake(_events(30))
    assert 0.0 <= result["probability"] <= 1.0
    assert result["risk_level"] in ("very_low", "low", "moderate", "high")
    assert "features" in result

def test_predict_insufficient():
    result = predict_large_earthquake(_events(3))
    assert "error" in result

def test_features():
    f = _extract_features(_events(30))
    assert f is not None
    assert len(f) == 6
