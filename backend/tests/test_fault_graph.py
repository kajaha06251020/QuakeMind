import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.fault_graph import analyze_fault_interactions


def _clustered_events():
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"fg-{i}",
            magnitude=4.0 + i * 0.2,
            latitude=35.0 + i * 0.01,
            longitude=139.0 + i * 0.01,
            depth_km=10.0,
            timestamp=(base + timedelta(hours=i * 6)).isoformat(),
        )
        for i in range(10)
    ]


def test_analyze_interactions():
    result = analyze_fault_interactions(_clustered_events())
    assert result["n_events"] == 10
    assert result["n_edges"] > 0
    assert len(result["most_influential"]) > 0


def test_insufficient():
    result = analyze_fault_interactions(_clustered_events()[:2])
    assert "error" in result
