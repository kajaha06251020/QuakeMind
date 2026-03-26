"""ベイズ状態空間モデルのテスト。"""
import pytest
from app.usecases.state_space import kalman_stress_filter


def test_kalman_filter_keys():
    obs = [1.0, 2.0, 1.5, 3.0, 2.5, 2.0, 3.5, 4.0, 3.0, 2.0]
    result = kalman_stress_filter(obs)
    assert "estimated_states" in result
    assert "current_state" in result
    assert "trend" in result
    assert "trend_direction" in result
    assert result["trend_direction"] in ("increasing", "decreasing", "stable")


def test_kalman_filter_insufficient():
    result = kalman_stress_filter([1.0, 2.0])
    assert "error" in result


def test_kalman_filter_length_matches():
    obs = [float(i) for i in range(20)]
    result = kalman_stress_filter(obs)
    assert len(result["estimated_states"]) == 20
    assert len(result["uncertainties"]) == 20
    assert result["current_uncertainty"] >= 0
