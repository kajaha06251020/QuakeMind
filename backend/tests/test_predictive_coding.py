"""予測コーディングのテスト。"""
import pytest
from datetime import datetime, timedelta
from app.usecases.predictive_coding import compute_surprise
from app.domain.seismology import EarthquakeRecord


def _make_events(n=60, spread_days=30):
    base = datetime(2024, 1, 1)
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=3.0 + (i % 4) * 0.3,
            latitude=35.0, longitude=135.0,
            depth_km=10.0,
            timestamp=(base + timedelta(days=i % spread_days, hours=i % 24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        for i in range(n)
    ]


def test_compute_surprise_keys():
    events = _make_events(60, 30)
    result = compute_surprise(events, window_days=5)
    assert "mean_surprise" in result
    assert "recent_surprise" in result
    assert "alert" in result
    assert "recent_surprises" in result


def test_compute_surprise_insufficient():
    result = compute_surprise(_make_events(10))
    assert "error" in result


def test_compute_surprise_alert_is_bool():
    events = _make_events(60, 30)
    result = compute_surprise(events, window_days=5)
    assert isinstance(result["alert"], bool)
    assert isinstance(result["mean_surprise"], float)
