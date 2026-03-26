import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.counterfactual import counterfactual_analysis

def _events():
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(event_id="main-001", magnitude=7.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=base.isoformat()),
    ] + [
        EarthquakeRecord(event_id=f"as-{i}", magnitude=4.0, latitude=35.0 + i*0.01, longitude=139.0, depth_km=15.0,
            timestamp=(base + timedelta(hours=i)).isoformat())
        for i in range(1, 10)
    ]

def test_counterfactual_basic():
    result = counterfactual_analysis(_events(), "main-001")
    assert "actual_scenario" in result
    assert "counterfactual_scenario" in result
    assert "impact" in result
    assert result["impact"]["additional_events_caused"] >= 0

def test_counterfactual_not_found():
    result = counterfactual_analysis(_events(), "nonexistent")
    assert "error" in result

def test_counterfactual_small_event():
    result = counterfactual_analysis(_events(), "as-1")
    assert result["impact"]["additional_events_caused"] < result["removed_event"]["magnitude"]
