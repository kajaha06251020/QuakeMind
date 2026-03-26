import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.services.knowledge_gaps import detect_knowledge_gaps

def _sparse_events():
    return [EarthquakeRecord(event_id=f"kg-{i}", magnitude=3.0, latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp=(datetime(2026, 3, 25, tzinfo=timezone.utc) + timedelta(hours=i)).isoformat()) for i in range(5)]

def test_detect_gaps():
    result = detect_knowledge_gaps(_sparse_events())
    assert result["total_gaps"] > 0
    assert result["high_severity"] > 0  # 短期間データ

def test_no_events():
    result = detect_knowledge_gaps([])
    assert result["total_gaps"] >= 0

def test_with_analyses():
    result = detect_knowledge_gaps(_sparse_events(), {"etas_evaluated": True, "ml_evaluated": False})
    types = [g["type"] for g in result["gaps"]]
    assert "model_evaluation_gap" in types
