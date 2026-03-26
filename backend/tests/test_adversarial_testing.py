"""敵対的テストのテスト。"""
import pytest
from app.services.adversarial_testing import adversarial_test
from app.domain.seismology import EarthquakeRecord


def _make_events(n=30):
    return [
        EarthquakeRecord(
            event_id=str(i), magnitude=3.0 + (i % 5) * 0.4,
            latitude=35.0 + i * 0.01, longitude=135.0 + i * 0.01,
            depth_km=10.0, timestamp="2024-01-15T10:00:00Z",
        )
        for i in range(n)
    ]


def test_adversarial_keys():
    events = _make_events(30)
    result = adversarial_test(events, n_perturbations=4)
    assert "base_probability" in result
    assert "robustness_score" in result
    assert "vulnerability" in result
    assert result["vulnerability"] in ("robust", "moderate", "fragile")


def test_adversarial_insufficient_events():
    result = adversarial_test(_make_events(5))
    assert "error" in result


def test_adversarial_robustness_range():
    events = _make_events(30)
    result = adversarial_test(events, n_perturbations=4)
    assert 0.0 <= result["robustness_score"] <= 1.0
    assert result["n_perturbations"] == 4
