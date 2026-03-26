import numpy as np
from app.usecases.information_theory import mutual_information, analyze_parameter_dependencies


def test_high_mi():
    rng = np.random.default_rng(42)
    x = rng.uniform(0, 10, 200)
    y = x + rng.normal(0, 0.1, 200)  # highly correlated
    mi = mutual_information(x, y)
    assert mi > 0.5


def test_independent():
    rng = np.random.default_rng(42)
    x = rng.uniform(0, 10, 200)
    y = rng.uniform(0, 10, 200)
    mi = mutual_information(x, y)
    assert mi < 1.0


def test_analyze_params():
    rng = np.random.default_rng(42)
    n = 100
    result = analyze_parameter_dependencies(
        rng.uniform(2, 7, n), rng.uniform(5, 100, n),
        rng.uniform(30, 45, n), rng.uniform(128, 146, n),
    )
    assert "mutual_information" in result
    assert len(result["mutual_information"]) == 6  # C(4,2)=6 pairs
