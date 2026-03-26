import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

async def _seed(n=30):
    import random
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        for i in range(n):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"dash-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 6.0), 1),
                depth_km=20.0, latitude=35.0, longitude=139.0, region="東京都",
                occurred_at=datetime(2026, 3, 1, tzinfo=timezone.utc) + timedelta(days=random.uniform(0, 25)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_overview(async_client, db_engine):
    resp = await async_client.get("/research-dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "journal" in data
    assert "active_hypotheses" in data

@pytest.mark.asyncio
async def test_run_hourly(async_client, db_engine):
    await _seed()
    resp = await async_client.post("/research-dashboard/run/hourly")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_journal_endpoint(async_client, db_engine):
    resp = await async_client.get("/research-dashboard/journal")
    assert resp.status_code == 200
    assert "entries" in resp.json()

@pytest.mark.asyncio
async def test_hypotheses_endpoint(async_client, db_engine):
    resp = await async_client.get("/research-dashboard/hypotheses")
    assert resp.status_code == 200
