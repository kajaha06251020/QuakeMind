"""異常検知 + 静穏化検出のテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.anomaly_detection import detect_anomaly, detect_quiescence


def _make_normal_events(n: int = 60, days: int = 60) -> list[EarthquakeRecord]:
    """均等に分布したイベント（正常活動）。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"norm-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        )
        for i in range(n)
    ]


def _make_anomalous_events() -> list[EarthquakeRecord]:
    """直近7日に大量のイベントが集中。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    # 背景: 53日間で1件/日
    for i in range(53):
        events.append(EarthquakeRecord(
            event_id=f"bg-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        ))
    # 直近7日: 1日10件
    for i in range(70):
        events.append(EarthquakeRecord(
            event_id=f"anom-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=53 + i / 10)).isoformat(),
        ))
    return events


def _make_quiescent_events() -> list[EarthquakeRecord]:
    """直近30日で活動が激減。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    # 前半150日: 1件/日
    for i in range(150):
        events.append(EarthquakeRecord(
            event_id=f"active-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        ))
    # 直近30日: 2件のみ（150日の活動期間から十分な間隔を空ける）
    for i in range(2):
        events.append(EarthquakeRecord(
            event_id=f"quiet-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=185 + i * 10)).isoformat(),
        ))
    return events


def test_anomaly_normal():
    events = _make_normal_events()
    result = detect_anomaly(events, evaluation_days=7)
    assert result["is_anomalous"] is False


def test_anomaly_detected():
    events = _make_anomalous_events()
    result = detect_anomaly(events, evaluation_days=7)
    assert result["is_anomalous"] is True
    assert result["p_value"] < 0.05
    assert result["recent_rate"] > result["background_rate"]


def test_anomaly_insufficient_data():
    events = [EarthquakeRecord(
        event_id="x", magnitude=3.0, latitude=35.0, longitude=139.0,
        depth_km=10.0, timestamp="2026-03-01T00:00:00+00:00",
    )]
    result = detect_anomaly(events)
    assert result["is_anomalous"] is False


def test_quiescence_normal():
    events = _make_normal_events()
    result = detect_quiescence(events, evaluation_days=30)
    assert result["is_quiescent"] is False


def test_quiescence_detected():
    events = _make_quiescent_events()
    result = detect_quiescence(events, evaluation_days=30)
    assert result["is_quiescent"] is True
    assert result["ratio"] < 0.5
