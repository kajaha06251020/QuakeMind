import numpy as np
from app.usecases.fluid_correlation import correlate_fluid_signals

def test_correlated():
    rng = np.random.default_rng(42)
    rain = rng.uniform(0, 50, 100)
    eq = rain * 0.1 + rng.normal(0, 0.5, 100)  # correlated
    result = correlate_fluid_signals(eq, precipitation_mm=rain)
    assert result["correlations"]["precipitation"]["simultaneous_r"] > 0.3

def test_uncorrelated():
    rng = np.random.default_rng(42)
    eq = rng.uniform(0, 5, 100)
    rain = rng.uniform(0, 50, 100)
    result = correlate_fluid_signals(eq, precipitation_mm=rain)
    assert abs(result["correlations"]["precipitation"]["simultaneous_r"]) < 0.5

def test_no_signals():
    result = correlate_fluid_signals(np.array([1, 2, 3]))
    assert "note" in result
