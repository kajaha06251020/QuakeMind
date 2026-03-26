"""最適観測設計のテスト。"""
import pytest
from app.usecases.optimal_observation import recommend_observation_sites
from app.domain.seismology import EarthquakeRecord


def _make_events(n=10):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=3.5,
            latitude=35.0 + i * 0.05, longitude=135.0 + i * 0.05,
            depth_km=10.0, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


def test_recommend_keys():
    result = recommend_observation_sites(_make_events(10), n_recommendations=3)
    assert "recommendations" in result
    assert len(result["recommendations"]) == 3


def test_recommend_empty_events():
    result = recommend_observation_sites([], n_recommendations=3)
    assert "recommendations" in result
    assert len(result["recommendations"]) == 3


def test_recommend_fields():
    result = recommend_observation_sites(_make_events(10), n_recommendations=2)
    for rec in result["recommendations"]:
        assert "name" in rec
        assert "total_score" in rec
    assert "all_candidates" in result
    assert len(result["all_candidates"]) == 8  # 8 candidate sites
