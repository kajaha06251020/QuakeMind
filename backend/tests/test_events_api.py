"""GET /events エンドポイントのテスト。"""
import uuid
import pytest
from datetime import datetime, timezone

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_events(count: int = 5):
    factory = get_session_factory()
    async with factory() as session:
        for i in range(count):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=f"seed-{uuid.uuid4().hex[:8]}-{i:03d}",
                source="p2p",
                magnitude=3.0 + i * 0.5,
                depth_km=10.0 + i,
                latitude=35.0 + i * 0.1,
                longitude=139.0,
                region="東京都" if i % 2 == 0 else "大阪府",
                occurred_at=datetime(2026, 3, 26, 10, i, 0, tzinfo=timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_events_empty(async_client, db_engine):
    resp = await async_client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_events_with_data(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["events"]) == 5


@pytest.mark.asyncio
async def test_get_events_filter_magnitude(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?min_magnitude=4.5")
    assert resp.status_code == 200
    data = resp.json()
    for ev in data["events"]:
        assert ev["magnitude"] >= 4.5


@pytest.mark.asyncio
async def test_get_events_filter_region(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?region=東京都")
    assert resp.status_code == 200
    data = resp.json()
    for ev in data["events"]:
        assert ev["region"] == "東京都"


@pytest.mark.asyncio
async def test_get_events_pagination(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?limit=2&offset=0")
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["total"] == 5
