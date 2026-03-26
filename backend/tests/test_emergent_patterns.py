"""創発パターン検出のテスト。"""
import pytest
from app.usecases.emergent_patterns import detect_emergent_patterns
from app.domain.seismology import EarthquakeRecord


def _make_events(n=30):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=3.0 + (i % 5) * 0.4,
            latitude=35.0 + (i % 10) * 0.1, longitude=135.0 + (i % 8) * 0.15,
            depth_km=5.0 + (i % 4) * 5, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


def test_emergent_patterns_keys():
    events = _make_events(30)
    result = detect_emergent_patterns(events, n_clusters=3)
    assert "n_patterns" in result
    assert "n_anomalous" in result
    assert "patterns" in result
    assert "interpretation" in result


def test_emergent_patterns_insufficient():
    result = detect_emergent_patterns(_make_events(10))
    assert "error" in result


def test_emergent_patterns_structure():
    events = _make_events(30)
    result = detect_emergent_patterns(events, n_clusters=3)
    assert result["n_patterns"] > 0
    for p in result["patterns"]:
        assert "cluster_id" in p
        assert "novelty_score" in p
        assert "n_events" in p
