import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.bayesian_etas import bayesian_etas_forecast

def _events(n=30):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"be-{i}", magnitude=round(random.uniform(2.5, 6.0), 1),
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp=(base + timedelta(days=random.uniform(0, 90))).isoformat()) for i in range(n)]

def test_bayesian_basic():
    result = bayesian_etas_forecast(_events(30), forecast_hours=72, n_samples=50, burn_in=10)
    assert "expected_events" in result
    assert "ci_2_5" in result["expected_events"]
    assert "ci_97_5" in result["expected_events"]
    assert "posterior_parameters" in result
    assert result["expected_events"]["ci_2_5"] <= result["expected_events"]["ci_97_5"]

def test_bayesian_has_uncertainty():
    result = bayesian_etas_forecast(_events(30), n_samples=50, burn_in=10)
    assert result["expected_events"]["std"] >= 0
    for p in result["posterior_parameters"].values():
        assert p["ci_2_5"] <= p["mean"] <= p["ci_97_5"]

def test_bayesian_insufficient():
    result = bayesian_etas_forecast(_events(5), n_samples=50, burn_in=10)
    assert "error" in result
