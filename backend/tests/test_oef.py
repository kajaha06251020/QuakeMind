import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.oef import generate_oef_forecast

def _events(n=30):
    import random
    random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"oef-{i}", magnitude=round(random.uniform(2.0, 5.5), 1),
        latitude=35.0, longitude=139.0, depth_km=10.0,
        timestamp=(base + timedelta(days=random.uniform(0, 60))).isoformat()) for i in range(n)]

@pytest.mark.asyncio
async def test_oef_basic():
    result = await generate_oef_forecast(_events(30))
    assert "forecasts" in result
    assert "24h" in result["forecasts"]
    assert "7d" in result["forecasts"]
    assert "30d" in result["forecasts"]
    for f in result["forecasts"].values():
        assert 0 <= f["probability"] <= 1
        assert f["ci_95"]["lower"] <= f["ci_95"]["upper"]

@pytest.mark.asyncio
async def test_oef_insufficient():
    result = await generate_oef_forecast(_events(5))
    assert "error" in result

@pytest.mark.asyncio
async def test_oef_has_model_weights():
    result = await generate_oef_forecast(_events(30))
    assert "model_weights_used" in result
    for f in result["forecasts"].values():
        assert len(f["model_contributions"]) == 3
