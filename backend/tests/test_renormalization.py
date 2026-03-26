"""くりこみ群解析のテスト。"""
import pytest
from app.usecases.renormalization import renormalization_analysis
from app.domain.seismology import EarthquakeRecord


def _make_events(n=50):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=2.0 + (i % 15) * 0.3,
            latitude=35.0 + i * 0.01, longitude=135.0 + i * 0.01,
            depth_km=10.0, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


def test_renormalization_keys():
    events = _make_events(50)
    result = renormalization_analysis(events)
    assert "b_value" in result
    assert "scale_invariance_r2" in result
    assert "state" in result
    assert result["state"] in ("critical", "near_critical", "subcritical", "non_scaling")


def test_renormalization_insufficient():
    result = renormalization_analysis(_make_events(10))
    assert "error" in result


def test_renormalization_b_value_reasonable():
    events = _make_events(50)
    result = renormalization_analysis(events)
    assert 0.0 < result["b_value"] < 5.0
    assert 0.0 <= result["scale_invariance_r2"] <= 1.0
