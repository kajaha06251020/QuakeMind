import pytest
from app.services.hypothesis_engine import create_hypothesis, get_active_hypotheses, update_hypothesis, check_expired_hypotheses

@pytest.mark.asyncio
async def test_create_and_get(db_engine):
    hyp_id = await create_hypothesis("b値低下は前兆", "東京都のb値が0.85に低下", region="東京都", trigger_event="b_value_drop")
    active = await get_active_hypotheses()
    assert len(active) >= 1
    assert active[0]["status"] == "monitoring"

@pytest.mark.asyncio
async def test_update_status(db_engine):
    hyp_id = await create_hypothesis("テスト仮説", "テスト")
    result = await update_hypothesis(hyp_id, "confirmed", {"note": "M5.5が発生"})
    assert result is not None
    assert result["status"] == "confirmed"
    assert result["resolved_at"] is not None

@pytest.mark.asyncio
async def test_check_expired(db_engine):
    # verify_after_days=0 で即期限切れ
    await create_hypothesis("即期限切れ", "テスト", verify_after_days=0)
    expired = await check_expired_hypotheses()
    assert expired >= 1
