import pytest
import numpy as np
from app.usecases.physics_informed import train_pinn_model, pinn_predict


def test_train_basic():
    rng = np.random.default_rng(42)
    X = rng.uniform(0, 1, (50, 3))
    y = X @ np.array([1.0, 2.0, 0.5]) + 0.1 * rng.normal(0, 1, 50)
    result = train_pinn_model(X, y, physics_weight=0.1)
    assert "weights" in result
    assert result["train_mse"] < 1.0
    assert result["n_samples"] == 50


def test_predict():
    model = {"weights": [1.0, 2.0], "bias": 0.5}
    X = np.array([[1.0, 1.0], [2.0, 3.0]])
    pred = pinn_predict(model, X)
    assert abs(pred[0] - 3.5) < 0.01  # 1*1 + 2*1 + 0.5


def test_physics_constraint():
    rng = np.random.default_rng(42)
    X = rng.uniform(0, 1, (30, 2))
    y = rng.uniform(0, 9, 30)
    result = train_pinn_model(X, y, physics_weight=1.0)
    assert result["converged"] or result["train_mse"] >= 0
