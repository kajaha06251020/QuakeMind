"""連鎖確率マップのテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.chain_probability import compute_chain_probability


def _make_recent_events() -> list[EarthquakeRecord]:
    base = datetime(2026, 3, 25, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(event_id="big", magnitude=6.5, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=base.isoformat()),
        EarthquakeRecord(event_id="as1", magnitude=4.0, latitude=35.1, longitude=139.1, depth_km=15.0, timestamp=(base + timedelta(hours=2)).isoformat()),
        EarthquakeRecord(event_id="as2", magnitude=3.5, latitude=34.9, longitude=138.9, depth_km=20.0, timestamp=(base + timedelta(hours=5)).isoformat()),
    ]


def test_chain_basic():
    events = _make_recent_events()
    result = compute_chain_probability(events, forecast_hours=24, grid_spacing_deg=0.5, grid_radius_deg=2.0)
    assert "grid" in result
    assert "resolution_deg" in result
    assert len(result["grid"]) > 0
    for cell in result["grid"]:
        assert "lat" in cell
        assert "lon" in cell
        assert "probability" in cell
        assert 0.0 <= cell["probability"] <= 1.0


def test_chain_empty():
    result = compute_chain_probability([], forecast_hours=24)
    assert result["grid"] == []


def test_chain_higher_near_source():
    events = _make_recent_events()
    result = compute_chain_probability(events, forecast_hours=24, grid_spacing_deg=0.5, grid_radius_deg=2.0)
    # 震源に近いグリッドの確率が高いことを確認
    near = [c for c in result["grid"] if abs(c["lat"] - 35.0) < 0.6 and abs(c["lon"] - 139.0) < 0.6]
    far = [c for c in result["grid"] if abs(c["lat"] - 35.0) > 1.5 or abs(c["lon"] - 139.0) > 1.5]
    if near and far:
        avg_near = sum(c["probability"] for c in near) / len(near)
        avg_far = sum(c["probability"] for c in far) / len(far)
        assert avg_near > avg_far
