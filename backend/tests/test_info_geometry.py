"""情報幾何学のテスト。"""
import numpy as np
import pytest
from app.usecases.info_geometry import fisher_information, compute_distribution_change


def test_fisher_information_identical():
    counts = np.array([5.0, 3.0, 2.0, 1.0])
    fi = fisher_information(counts, counts)
    assert fi == pytest.approx(0.0, abs=1e-5)


def test_fisher_information_different():
    before = np.array([10.0, 5.0, 2.0, 1.0])
    after = np.array([1.0, 2.0, 5.0, 10.0])
    fi = fisher_information(before, after)
    assert fi > 0


def test_compute_distribution_change_keys():
    mags = np.array([3.0 + (i % 10) * 0.2 for i in range(40)])
    result = compute_distribution_change(mags)
    assert "kl_divergence" in result
    assert "significant_change" in result
    assert "interpretation" in result


def test_compute_distribution_change_insufficient():
    result = compute_distribution_change(np.array([3.0, 3.5, 4.0]))
    assert "error" in result
