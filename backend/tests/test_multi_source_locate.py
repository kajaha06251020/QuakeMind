import pytest
from app.domain.seismology import EarthquakeRecord
from app.usecases.multi_source_locate import locate_multi_source

def test_merge_close_events():
    events = [
        EarthquakeRecord(event_id="p2p-001", magnitude=5.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp="2026-03-25T10:00:00+00:00"),
        EarthquakeRecord(event_id="usgs-001", magnitude=5.1, latitude=35.02, longitude=139.01, depth_km=12.0, timestamp="2026-03-25T10:01:00+00:00"),
    ]
    result = locate_multi_source(events)
    assert len(result) >= 1
    assert result[0]["n_sources"] == 2
    assert 34.9 < result[0]["merged_lat"] < 35.1

def test_no_merge_far_events():
    events = [
        EarthquakeRecord(event_id="a", magnitude=5.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp="2026-03-25T10:00:00+00:00"),
        EarthquakeRecord(event_id="b", magnitude=5.0, latitude=40.0, longitude=140.0, depth_km=10.0, timestamp="2026-03-25T10:00:00+00:00"),
    ]
    result = locate_multi_source(events)
    assert len(result) == 0  # 距離が離れすぎてマッチしない

def test_empty_events():
    assert locate_multi_source([]) == []
