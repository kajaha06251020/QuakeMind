import pytest
from app.services.model_evaluator import evaluate_etas_accuracy, evaluate_ml_accuracy

@pytest.mark.asyncio
async def test_etas_eval(db_engine):
    preds = [{"expected_events": 3.0, "actual_events": 2}, {"expected_events": 5.0, "actual_events": 6}]
    result = await evaluate_etas_accuracy(preds)
    assert result["mae"] >= 0
    assert result["rmse"] >= 0

@pytest.mark.asyncio
async def test_ml_eval(db_engine):
    preds = [
        {"predicted_prob": 0.8, "actual_occurred": True},
        {"predicted_prob": 0.3, "actual_occurred": False},
        {"predicted_prob": 0.6, "actual_occurred": False},
    ]
    result = await evaluate_ml_accuracy(preds)
    assert 0 <= result["accuracy"] <= 1
    assert "confusion_matrix" in result

@pytest.mark.asyncio
async def test_eval_empty(db_engine):
    result = await evaluate_etas_accuracy([])
    assert "error" in result
