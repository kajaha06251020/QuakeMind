from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.stress_history import compute_cumulative_stress


def _events():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(event_id=f"sh-{i}", magnitude=5.0 + i*0.5, latitude=35.0 + i*0.1, longitude=139.0, depth_km=10.0,
            timestamp=(base + timedelta(days=i*30)).isoformat())
        for i in range(5)
    ]


def test_cumulative_stress():
    result = compute_cumulative_stress(_events(), 35.0, 139.0)
    assert result["cumulative_stress_mpa"] != 0
    assert result["n_contributing_events"] > 0
    assert len(result["history"]) > 0


def test_empty_events():
    result = compute_cumulative_stress([], 35.0, 139.0)
    assert result["cumulative_stress_mpa"] == 0


def test_far_target():
    result = compute_cumulative_stress(_events(), 25.0, 125.0)  # 沖縄（遠い）
    assert result["n_contributing_events"] == 0
