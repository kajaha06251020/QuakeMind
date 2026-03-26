import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB
from app.services.research_workflow import investigate_anomaly, investigate_large_earthquake

async def _seed(n=30):
    import random
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(n):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"wf-{i:04d}",
                source="p2p", magnitude=round(random.uniform(2.0, 7.0), 1),
                depth_km=20.0, latitude=35.0 + random.uniform(-1, 1),
                longitude=139.0 + random.uniform(-1, 1), region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 25)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_investigate_anomaly(db_engine):
    await _seed()
    result = await investigate_anomaly("東京都")
    assert "steps" in result
    assert len(result["steps"]) >= 3

@pytest.mark.asyncio
async def test_investigate_large_eq(db_engine):
    await _seed()
    result = await investigate_large_earthquake("wf-0000")
    assert "etas_forecast" in result or "error" in result

@pytest.mark.asyncio
async def test_investigate_no_data(db_engine):
    result = await investigate_anomaly("存在しない地域")
    assert result["status"] == "insufficient_data"
