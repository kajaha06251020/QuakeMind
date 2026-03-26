from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.usecases.risk_profile import compute_risk_profile

def _events(n=10, base_mag=4.0):
    return [EarthquakeRecord(event_id=f"rp-{i}", magnitude=base_mag + i*0.1, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(n)]

def test_profile_with_faults():
    result = compute_risk_profile("東京都", _events())
    assert result["risk_score"] >= 0
    assert len(result["active_faults"]) > 0
    assert "risk_level" in result

def test_profile_unknown_region():
    result = compute_risk_profile("未知の地域", _events())
    assert result["active_faults"] == []

def test_profile_no_events():
    result = compute_risk_profile("東京都", [])
    assert result["historical_statistics"]["total_events"] == 0
