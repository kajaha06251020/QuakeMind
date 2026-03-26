import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB
from app.services.research_scheduler import hourly_analysis, daily_analysis, weekly_analysis

async def _seed(n=50):
    import random
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(n):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"sched-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 6.0), 1),
                depth_km=20.0, latitude=35.0 + random.uniform(-2, 2),
                longitude=139.0 + random.uniform(-2, 2), region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 180)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_hourly(db_engine):
    await _seed()
    result = await hourly_analysis()
    assert "is_anomalous" in result or "status" in result

@pytest.mark.asyncio
async def test_daily(db_engine):
    await _seed(100)
    result = await daily_analysis()
    assert "n_clusters" in result or "status" in result

@pytest.mark.asyncio
async def test_weekly(db_engine):
    await _seed(100)
    result = await weekly_analysis()
    assert "etas" in result or "status" in result

@pytest.mark.asyncio
async def test_hourly_no_data(db_engine):
    result = await hourly_analysis()
    assert result["status"] == "no_data"
