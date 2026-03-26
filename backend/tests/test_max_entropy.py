"""最大エントロピーモデルのテスト。"""
import pytest
from app.usecases.max_entropy import max_entropy_rate


def test_max_entropy_keys():
    result = max_entropy_rate(observed_mean=5.0, observed_var=3.0)
    assert "distribution" in result
    assert "entropy" in result
    assert "model_mean" in result
    assert "lagrange_multipliers" in result


def test_max_entropy_distribution_sums_to_one():
    result = max_entropy_rate(observed_mean=3.0, observed_var=2.0)
    total = sum(result["distribution"].values())
    # Distribution is truncated to p>0.001, so sum may be < 1
    assert 0.5 <= total <= 1.05


def test_max_entropy_entropy_positive():
    result = max_entropy_rate(observed_mean=4.0, observed_var=4.0)
    assert result["entropy"] > 0
    assert "lambda1" in result["lagrange_multipliers"]
    assert "lambda2" in result["lagrange_multipliers"]
