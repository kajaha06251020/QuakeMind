import pytest
from app.services.self_improvement import verify_and_update, get_model_weights, get_improvement_summary


@pytest.mark.asyncio
async def test_verify_correct(db_engine):
    result = await verify_and_update("etas", 0.8, True)
    assert result["accuracy"] == "的中"
    assert result["new_weight"] > 0


@pytest.mark.asyncio
async def test_verify_wrong(db_engine):
    result = await verify_and_update("ml", 0.8, False)
    assert result["accuracy"] == "外れ"


def test_get_weights():
    w = get_model_weights()
    assert "etas" in w
    assert sum(w.values()) > 0


def test_summary():
    s = get_improvement_summary()
    assert "current_weights" in s
