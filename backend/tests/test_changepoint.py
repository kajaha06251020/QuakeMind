import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.changepoint import detect_rate_changepoints, detect_b_value_changepoints

def _normal_then_spike():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    # 前半30日: 1件/日
    for d in range(30):
        events.append(EarthquakeRecord(event_id=f"n-{d}", magnitude=3.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=d)).isoformat()))
    # 後半30日: 5件/日
    for d in range(30, 60):
        for i in range(5):
            events.append(EarthquakeRecord(event_id=f"s-{d}-{i}", magnitude=3.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=d, hours=i)).isoformat()))
    return events

def test_detect_rate_changepoint():
    events = _normal_then_spike()
    result = detect_rate_changepoints(events, window_days=7)
    assert len(result["changepoints"]) >= 1
    types = [cp["type"] for cp in result["changepoints"]]
    assert "increase" in types

def test_no_changepoint_uniform():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [EarthquakeRecord(event_id=f"u-{d}", magnitude=3.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp=(base + timedelta(days=d)).isoformat()) for d in range(60)]
    result = detect_rate_changepoints(events)
    # 均一なデータは変化点が少ないはず
    assert len(result["changepoints"]) <= 1

def test_b_value_changepoints():
    ts = [{"start": f"2026-{m:02d}", "b_value": 1.0} for m in range(1, 6)]
    ts += [{"start": f"2026-{m:02d}", "b_value": 0.6} for m in range(6, 11)]
    result = detect_b_value_changepoints(ts)
    assert len(result) >= 1
    assert result[0]["type"] == "decrease"

def test_insufficient_data():
    result = detect_rate_changepoints([])
    assert result["changepoints"] == []
