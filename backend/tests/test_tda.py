import pytest
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
from app.usecases.tda import compute_persistence


def _clustered():
    return [EarthquakeRecord(event_id=f"tda-{i}", magnitude=4.0, latitude=35.0 + i*0.01, longitude=139.0 + i*0.01, depth_km=10.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(20)]


def _scattered():
    return [EarthquakeRecord(event_id=f"tda-{i}", magnitude=4.0, latitude=30.0 + i*0.5, longitude=130.0 + i*0.5, depth_km=10.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(20)]


def test_persistence_basic():
    result = compute_persistence(_clustered())
    assert "betti_curve" in result
    assert result["mean_persistence_km"] >= 0


def test_clustered_vs_scattered():
    cl = compute_persistence(_clustered())
    sc = compute_persistence(_scattered())
    # 散在は永続性が高い（成分がなかなかマージしない）
    assert sc["max_persistence_km"] >= cl["max_persistence_km"]


def test_insufficient():
    result = compute_persistence(_clustered()[:2])
    assert "error" in result
