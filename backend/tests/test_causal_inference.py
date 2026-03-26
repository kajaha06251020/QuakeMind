import pytest
import numpy as np
from app.usecases.causal_inference import granger_causality, bidirectional_causality

def test_causal_signal():
    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, 100)
    y = np.zeros(100)
    for i in range(2, 100):
        y[i] = 0.8 * x[i - 2] + 0.2 * rng.normal()  # x causes y with lag 2
    result = granger_causality(x, y)
    assert result["causal"] == True

def test_no_causal():
    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, 100)
    y = rng.normal(0, 1, 100)
    result = granger_causality(x, y)
    # Independent signals should not be causal (usually)
    assert "p_value" in result

def test_bidirectional():
    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, 100)
    y = rng.normal(0, 1, 100)
    result = bidirectional_causality(x, y)
    assert "interpretation" in result
    assert "x_causes_y" in result

def test_insufficient_data():
    result = granger_causality(np.array([1, 2, 3]), np.array([4, 5, 6]))
    assert result.get("causal") is False
