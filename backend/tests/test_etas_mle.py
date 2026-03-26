import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.etas_mle import estimate_etas_parameters


def _synthetic_events(n=50):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"syn-{i}", magnitude=round(random.uniform(2.0, 6.0), 1),
            latitude=35.0, longitude=139.0, depth_km=10.0,
            timestamp=(base + timedelta(days=random.uniform(0, 180))).isoformat(),
        ) for i in range(n)
    ]


def test_estimate_basic():
    result = estimate_etas_parameters(_synthetic_events(50))
    assert "mu" in result
    assert "K" in result
    assert "alpha" in result
    assert "c" in result
    assert "p" in result
    assert result["n_events"] == 50


def test_estimate_insufficient():
    result = estimate_etas_parameters(_synthetic_events(5))
    assert "error" in result


def test_estimate_converges():
    result = estimate_etas_parameters(_synthetic_events(100))
    assert result.get("converged") is not None
    assert result["mu"] > 0
    assert result["p"] > 0
