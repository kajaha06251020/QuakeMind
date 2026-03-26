from app.domain.seismology import EarthquakeRecord
from app.usecases.tectonic_classifier import classify_tectonic_type, classify_events


def test_subduction():
    e = EarthquakeRecord(event_id="t1", magnitude=7.0, latitude=38.0, longitude=143.0, depth_km=50.0, timestamp="2026-01-01T00:00:00Z")
    result = classify_tectonic_type(e)
    assert result["type"] == "subduction_interface"
    assert "日本海溝" in result["zone"]


def test_crustal():
    e = EarthquakeRecord(event_id="t2", magnitude=5.0, latitude=35.5, longitude=139.5, depth_km=10.0, timestamp="2026-01-01T00:00:00Z")
    result = classify_tectonic_type(e)
    assert result["type"] == "crustal"


def test_deep_focus():
    e = EarthquakeRecord(event_id="t3", magnitude=6.0, latitude=35.0, longitude=139.0, depth_km=400.0, timestamp="2026-01-01T00:00:00Z")
    result = classify_tectonic_type(e)
    assert result["type"] == "deep_focus"


def test_classify_events():
    events = [
        EarthquakeRecord(event_id="e1", magnitude=5.0, latitude=38.0, longitude=143.0, depth_km=50.0, timestamp="2026-01-01T00:00:00Z"),
        EarthquakeRecord(event_id="e2", magnitude=4.0, latitude=35.5, longitude=139.5, depth_km=10.0, timestamp="2026-01-01T00:00:00Z"),
    ]
    result = classify_events(events)
    assert result["total"] == 2
    assert result["dominant_type"] is not None
