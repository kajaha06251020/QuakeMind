import pytest
from app.usecases.ensemble import bayesian_model_averaging, update_model_weights

def test_bma_basic():
    preds = [
        {"name": "etas", "probability": 0.3, "weight": 2.0, "uncertainty": 0.1},
        {"name": "ml", "probability": 0.5, "weight": 1.0, "uncertainty": 0.15},
        {"name": "coulomb", "probability": 0.2, "weight": 1.5, "uncertainty": 0.08},
    ]
    result = bayesian_model_averaging(preds)
    assert 0 <= result["ensemble_probability"] <= 1
    assert result["ci_95"]["lower"] <= result["ensemble_probability"] <= result["ci_95"]["upper"]
    assert result["n_models"] == 3

def test_bma_single_model():
    preds = [{"name": "etas", "probability": 0.4, "weight": 1.0, "uncertainty": 0.1}]
    result = bayesian_model_averaging(preds)
    assert abs(result["ensemble_probability"] - 0.4) < 0.01

def test_bma_empty():
    result = bayesian_model_averaging([])
    assert "error" in result

def test_weight_update():
    # Use unnormalized priors so relative shift is measurable.
    # After two updates: ETAS gets likelihood=0.8, ML gets likelihood=0.2 (wrong pred).
    weights = {"etas": 1.0, "ml": 1.0}
    # ETAS predicted 0.8, actual=True → high likelihood, weight increases relative to ml
    w1 = update_model_weights(weights, "etas", 0.8, True, learning_rate=1.0)
    # ML predicted 0.8, actual=False → low likelihood, weight decreases
    updated = update_model_weights(w1, "ml", 0.8, False, learning_rate=1.0)
    assert updated["etas"] > updated["ml"]

def test_weight_update_wrong_prediction():
    weights = {"etas": 1.0, "ml": 1.0}
    # ETAS predicted 0.8, actual=False → ETAS should lose weight relative to unchanged ml
    # Apply two steps: etas wrong (0.8, False), ml correct (0.8, True)
    w1 = update_model_weights(weights, "etas", 0.8, False, learning_rate=1.0)
    updated = update_model_weights(w1, "ml", 0.8, True, learning_rate=1.0)
    assert updated["etas"] < updated["ml"]
