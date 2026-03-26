import pytest
from app.services.llm_hypothesis import generate_hypotheses_from_analysis

@pytest.mark.asyncio
async def test_b_value_hypothesis(db_engine):
    results = {"b_value_change": -0.25, "b_value_latest": 0.75}
    hypotheses = await generate_hypotheses_from_analysis(results)
    assert any("b値" in h["title"] for h in hypotheses)

@pytest.mark.asyncio
async def test_anomaly_hypothesis(db_engine):
    results = {"anomaly_detected": True, "p_value": 0.001}
    hypotheses = await generate_hypotheses_from_analysis(results)
    assert any("活発化" in h["title"] for h in hypotheses)

@pytest.mark.asyncio
async def test_default_hypothesis(db_engine):
    results = {}
    hypotheses = await generate_hypotheses_from_analysis(results)
    assert len(hypotheses) >= 1
    assert "背景レベル" in hypotheses[0]["title"]

@pytest.mark.asyncio
async def test_multiple_triggers(db_engine):
    results = {"b_value_change": -0.3, "b_value_latest": 0.7, "n_clusters": 3, "anomaly_detected": True, "p_value": 0.01}
    hypotheses = await generate_hypotheses_from_analysis(results)
    assert len(hypotheses) >= 3
