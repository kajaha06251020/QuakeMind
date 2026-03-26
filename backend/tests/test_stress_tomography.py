import pytest
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.usecases.stress_tomography import compute_3d_stress_field

def _events(n=20):
    import random; random.seed(42)
    return [EarthquakeRecord(event_id=f"st-{i}", magnitude=random.uniform(3, 6), latitude=35+random.uniform(-1,1), longitude=139+random.uniform(-1,1), depth_km=random.uniform(5,50), timestamp=datetime.now(timezone.utc).isoformat()) for i in range(n)]

def test_basic():
    result = compute_3d_stress_field(_events(), grid_spacing_deg=1.0, depth_layers=[15, 30])
    assert result["grid_points"] > 0
    assert len(result["hotspots"]) > 0

def test_insufficient():
    result = compute_3d_stress_field(_events(3))
    assert "error" in result
