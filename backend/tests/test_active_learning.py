import pytest
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.services.active_learning import identify_data_gaps, compute_model_uncertainty_map

def _events_tokyo(n=30):
    return [EarthquakeRecord(event_id=f"al-{i}", magnitude=4.0, latitude=35.5 + i*0.01, longitude=139.5, depth_km=10.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(n)]

def test_identify_gaps():
    result = identify_data_gaps(_events_tokyo())
    assert len(result["data_gaps"]) > 0
    # Tokyo-concentrated data should show gaps in other regions
    high_priority = [g for g in result["data_gaps"] if g["priority"] == "high"]
    assert len(high_priority) > 0

def test_uncertainty_map():
    result = compute_model_uncertainty_map(_events_tokyo())
    assert len(result) > 0
    # Tokyo area should have lower uncertainty
    kanto = next(r for r in result if r["region"] == "関東")
    okinawa = next(r for r in result if r["region"] == "沖縄")
    assert kanto["prediction_uncertainty"] < okinawa["prediction_uncertainty"]

def test_empty_events():
    result = identify_data_gaps([])
    assert result["n_events_total"] == 0
