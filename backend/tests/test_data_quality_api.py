import uuid, pytest, random
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

async def _seed():
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(10):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"dq-{i:03d}", source="p2p",
                magnitude=round(random.uniform(3.0, 5.0), 1), depth_km=20.0,
                latitude=35.0+random.uniform(-0.5, 0.5), longitude=139.0+random.uniform(-0.5, 0.5),
                region="東京都", occurred_at=base+timedelta(days=i), fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_quality_scores(async_client, db_engine):
    now = datetime.now(timezone.utc).isoformat()
    with patch("app.usecases.data_quality.get_source_status", return_value={"p2p": {"last_fetch_at": now, "last_error": None}}):
        resp = await async_client.get("/data-quality/scores")
    assert resp.status_code == 200
    assert "overall_score" in resp.json()

@pytest.mark.asyncio
async def test_multi_source_locate_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/data-quality/multi-source-locate")
    assert resp.status_code == 200
    assert "merged_events" in resp.json()
