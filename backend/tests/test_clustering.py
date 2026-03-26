"""時空間クラスタリングのテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.clustering import detect_clusters


def _make_clustered_events() -> list[EarthquakeRecord]:
    """2つのクラスタ + ノイズを生成。"""
    events = []
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    # クラスタ1: 東京付近、3日間で5イベント
    for i in range(5):
        events.append(EarthquakeRecord(
            event_id=f"c1-{i}", magnitude=3.0 + i * 0.1,
            latitude=35.68 + i * 0.01, longitude=139.76 + i * 0.01,
            depth_km=20.0, timestamp=(base + timedelta(hours=i * 12)).isoformat(),
        ))
    # クラスタ2: 大阪付近、3日間で4イベント
    for i in range(4):
        events.append(EarthquakeRecord(
            event_id=f"c2-{i}", magnitude=4.0,
            latitude=34.69 + i * 0.01, longitude=135.50 + i * 0.01,
            depth_km=30.0, timestamp=(base + timedelta(days=10, hours=i * 12)).isoformat(),
        ))
    # ノイズ: 離れた場所
    events.append(EarthquakeRecord(
        event_id="noise-0", magnitude=2.5,
        latitude=43.0, longitude=141.0,
        depth_km=50.0, timestamp=(base + timedelta(days=5)).isoformat(),
    ))
    return events


def test_detect_clusters_finds_groups():
    events = _make_clustered_events()
    result = detect_clusters(events)
    assert result["n_clusters"] >= 1
    assert len(result["clusters"]) == result["n_clusters"]


def test_detect_clusters_has_required_fields():
    events = _make_clustered_events()
    result = detect_clusters(events)
    for c in result["clusters"]:
        assert "cluster_id" in c
        assert "n_events" in c
        assert "center_lat" in c
        assert "center_lon" in c
        assert "max_magnitude" in c


def test_detect_clusters_too_few_events():
    events = [EarthquakeRecord(
        event_id="solo", magnitude=3.0, latitude=35.0, longitude=139.0,
        depth_km=10.0, timestamp="2026-03-01T00:00:00+00:00",
    )]
    result = detect_clusters(events)
    assert result["n_clusters"] == 0


def test_detect_clusters_noise_count():
    events = _make_clustered_events()
    result = detect_clusters(events)
    assert result["noise_events"] >= 0
    total = sum(c["n_events"] for c in result["clusters"]) + result["noise_events"]
    assert total == len(events)
