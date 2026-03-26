from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.sequence_classifier import classify_sequence


def test_mainshock_aftershock():
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    events = [
        EarthquakeRecord(
            event_id=f"ma-{i}",
            magnitude=7.0 if i == 0 else 4.0 + i * 0.1,
            latitude=35.0,
            longitude=139.0,
            depth_km=10.0,
            timestamp=(base + timedelta(hours=i)).isoformat(),
        )
        for i in range(10)
    ]
    result = classify_sequence(events)
    assert result["type"] == "mainshock_aftershock"


def test_swarm():
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    events = [
        EarthquakeRecord(
            event_id=f"sw-{i}",
            magnitude=3.0 + (i % 3) * 0.1,
            latitude=35.0,
            longitude=139.0,
            depth_km=10.0,
            timestamp=(base + timedelta(hours=i)).isoformat(),
        )
        for i in range(15)
    ]
    result = classify_sequence(events)
    assert result["type"] == "swarm"


def test_insufficient():
    events = [
        EarthquakeRecord(
            event_id="x",
            magnitude=5.0,
            latitude=35.0,
            longitude=139.0,
            depth_km=10.0,
            timestamp="2026-01-01T00:00:00Z",
        )
    ]
    result = classify_sequence(events)
    assert result["type"] == "unclassified"
