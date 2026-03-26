"""時系列予測のテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.timeseries_forecast import forecast_daily_counts


def _make_daily_events(n_days: int = 60) -> list[EarthquakeRecord]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for d in range(n_days):
        count = 2 + (d % 7)  # 周期的パターン
        for i in range(count):
            events.append(EarthquakeRecord(
                event_id=f"ts-{d}-{i}", magnitude=3.0,
                latitude=35.0, longitude=139.0, depth_km=20.0,
                timestamp=(base + timedelta(days=d, hours=i)).isoformat(),
            ))
    return events


def test_forecast_basic():
    events = _make_daily_events(60)
    result = forecast_daily_counts(events, forecast_days=7)
    assert "forecast" in result
    assert len(result["forecast"]) == 7
    for entry in result["forecast"]:
        assert "date" in entry
        assert "expected_count" in entry
        assert entry["expected_count"] >= 0


def test_forecast_empty():
    result = forecast_daily_counts([], forecast_days=7)
    assert result["forecast"] == []


def test_forecast_short_history():
    events = _make_daily_events(3)
    result = forecast_daily_counts(events, forecast_days=7)
    assert len(result["forecast"]) == 7
