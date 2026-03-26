import uuid
import pytest
import random
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed():
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(20):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=f"res-{i:03d}",
                source="p2p",
                magnitude=round(random.uniform(2.0, 6.0), 1),
                depth_km=round(random.uniform(5, 50), 1),
                latitude=35.0 + random.uniform(-1, 1),
                longitude=139.0 + random.uniform(-1, 1),
                region="東京都",
                occurred_at=base + timedelta(days=i),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_briefing_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/research/briefing?days=7")
    assert resp.status_code == 200
    assert "summary" in resp.json()


@pytest.mark.asyncio
async def test_similar_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/research/similar?event_id=res-000")
    assert resp.status_code == 200
    data = resp.json()
    assert "similar_events" in data


@pytest.mark.asyncio
async def test_similar_not_found(async_client, db_engine):
    resp = await async_client.get("/research/similar?event_id=nonexistent")
    assert resp.status_code == 404
