"""フラクタル次元解析のテスト。"""
import pytest
import numpy as np
from app.usecases.fractal import compute_correlation_dimension


def test_clustered_points_low_d():
    rng = np.random.default_rng(42)
    lats = 35.0 + rng.normal(0, 0.01, 100)
    lons = 139.0 + rng.normal(0, 0.01, 100)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert 0.0 < d2 < 2.0


def test_scattered_points_high_d():
    rng = np.random.default_rng(42)
    lats = 30.0 + rng.uniform(0, 10, 200)
    lons = 130.0 + rng.uniform(0, 10, 200)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert d2 > 1.0


def test_too_few_points():
    d2 = compute_correlation_dimension(np.array([35.0, 35.1]), np.array([139.0, 139.1]))
    assert d2 is None


def test_identical_points():
    lats = np.full(50, 35.0)
    lons = np.full(50, 139.0)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert d2 < 0.5
