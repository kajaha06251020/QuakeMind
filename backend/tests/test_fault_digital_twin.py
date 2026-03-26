"""断層デジタルツインのテスト。"""
import pytest
from app.usecases.fault_digital_twin import compute_digital_twin
from app.domain.seismology import EarthquakeRecord


def _make_events(n=10):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=4.0 + (i % 3) * 0.5,
            latitude=34.0 + i * 0.1, longitude=136.0 + i * 0.05,
            depth_km=20.0, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


def test_digital_twin_keys():
    result = compute_digital_twin(_make_events(10))
    assert "faults" in result
    assert "most_loaded" in result
    assert "updated_at" in result


def test_digital_twin_fault_count():
    result = compute_digital_twin([])
    assert len(result["faults"]) == 6  # 6 defined faults


def test_digital_twin_fault_fields():
    result = compute_digital_twin(_make_events(5))
    for fault in result["faults"]:
        assert "fault_id" in fault
        assert "loading_percent" in fault
        assert "status" in fault
        assert fault["status"] in ("critical", "elevated", "normal")
        assert 0 <= fault["loading_percent"] <= 100
