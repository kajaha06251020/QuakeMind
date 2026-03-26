from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.usecases.induced_seismicity import classify_induced

def test_near_dam():
    events = [EarthquakeRecord(event_id="ind-1", magnitude=3.0, latitude=36.57, longitude=137.66, depth_km=5.0, timestamp=datetime.now(timezone.utc).isoformat())]
    result = classify_induced(events)
    assert result["likely_induced"] >= 1

def test_far_natural():
    events = [EarthquakeRecord(event_id="nat-1", magnitude=6.0, latitude=35.0, longitude=139.0, depth_km=50.0, timestamp=datetime.now(timezone.utc).isoformat())]
    result = classify_induced(events)
    assert result["natural"] >= 1
