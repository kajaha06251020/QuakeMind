import pytest
from app.domain.seismology import EarthquakeRecord
from app.usecases.similar_search import find_similar_events


def test_find_similar():
    target = EarthquakeRecord(
        event_id="target", magnitude=6.0,
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp="2026-03-25T00:00:00+00:00",
    )
    catalog = [
        EarthquakeRecord(
            event_id="sim1", magnitude=5.8,
            latitude=35.1, longitude=139.1, depth_km=12.0,
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        EarthquakeRecord(
            event_id="diff", magnitude=3.0,
            latitude=40.0, longitude=130.0, depth_km=80.0,
            timestamp="2026-02-01T00:00:00+00:00",
        ),
        target,  # 自分自身
    ]
    results = find_similar_events(target, catalog, max_results=5)
    assert len(results) >= 1
    assert results[0]["event_id"] == "sim1"


def test_find_similar_empty():
    target = EarthquakeRecord(
        event_id="t", magnitude=6.0,
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp="2026-03-25T00:00:00+00:00",
    )
    results = find_similar_events(target, [], max_results=5)
    assert results == []
