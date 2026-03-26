import pytest
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.usecases.uncertainty_decomposition import decompose_uncertainty


def _events(n):
    import random; random.seed(42)
    return [EarthquakeRecord(event_id=f"ud-{i}", magnitude=round(random.uniform(2, 6), 1), latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(n)]


def test_decompose():
    result = decompose_uncertainty(_events(50))
    assert result["total_uncertainty"] > 0
    assert 0 < result["aleatory_fraction"] <= 1.0
    assert 0 < result["epistemic_fraction"] <= 1.0
    assert result["aleatory_uncertainty"] > 0
    assert result["epistemic_uncertainty"] > 0


def test_more_data_less_epistemic():
    r50 = decompose_uncertainty(_events(50))
    r200 = decompose_uncertainty(_events(200))
    assert r200["epistemic_uncertainty"] < r50["epistemic_uncertainty"]
