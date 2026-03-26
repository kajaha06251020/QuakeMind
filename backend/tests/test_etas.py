"""ETAS 余震モデルのテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.etas import etas_forecast


def _make_mainshock_sequence() -> list[EarthquakeRecord]:
    base = datetime(2026, 3, 20, tzinfo=timezone.utc)
    events = [
        EarthquakeRecord(event_id="main", magnitude=7.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=base.isoformat()),
    ]
    for i in range(20):
        events.append(EarthquakeRecord(
            event_id=f"as-{i}", magnitude=4.0 + (i % 3) * 0.5,
            latitude=35.0 + i * 0.01, longitude=139.0 + i * 0.01, depth_km=15.0,
            timestamp=(base + timedelta(hours=i * 2)).isoformat(),
        ))
    return events


def test_etas_basic():
    events = _make_mainshock_sequence()
    result = etas_forecast(events, forecast_hours=72)
    assert "expected_events" in result
    assert "probability_m4_plus" in result
    assert result["forecast_hours"] == 72
    assert result["expected_events"] > 0


def test_etas_longer_forecast():
    events = _make_mainshock_sequence()
    r24 = etas_forecast(events, forecast_hours=24)
    r72 = etas_forecast(events, forecast_hours=72)
    assert r72["expected_events"] >= r24["expected_events"]


def test_etas_no_events():
    result = etas_forecast([], forecast_hours=24)
    assert result["expected_events"] == 0


def test_etas_single_small_event():
    events = [EarthquakeRecord(
        event_id="small", magnitude=2.0, latitude=35.0, longitude=139.0,
        depth_km=10.0, timestamp="2026-03-01T00:00:00+00:00",
    )]
    result = etas_forecast(events, forecast_hours=24)
    assert result["expected_events"] >= 0
