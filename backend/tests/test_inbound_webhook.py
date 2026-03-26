import pytest
from app.services.inbound_webhook import process_inbound_event

@pytest.mark.asyncio
async def test_inbound_valid(db_engine):
    result = await process_inbound_event({
        "magnitude": 5.0, "latitude": 35.0, "longitude": 139.0,
        "depth_km": 10.0, "region": "東京都",
    })
    assert result["status"] == "accepted"
    assert result["saved"] is True

@pytest.mark.asyncio
async def test_inbound_missing_fields(db_engine):
    result = await process_inbound_event({"magnitude": 5.0})
    assert "error" in result

@pytest.mark.asyncio
async def test_inbound_custom_id(db_engine):
    result = await process_inbound_event({
        "event_id": "custom-001", "magnitude": 4.0,
        "latitude": 35.0, "longitude": 139.0,
    })
    assert result["event_id"] == "custom-001"
