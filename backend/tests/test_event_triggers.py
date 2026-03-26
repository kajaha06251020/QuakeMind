import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.domain.models import EarthquakeEvent
from app.services.event_triggers import on_new_earthquake, on_b_value_change
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

async def _seed_for_triggers():
    import random
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(20):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"trig-{i:04d}",
                source="p2p", magnitude=round(random.uniform(2.0, 5.0), 1),
                depth_km=20.0, latitude=35.0, longitude=139.0, region="東京都",
                occurred_at=base + timedelta(days=i), fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_large_earthquake_trigger(db_engine):
    await _seed_for_triggers()
    event = EarthquakeEvent(event_id="trig-0001", magnitude=6.5, depth_km=10.0, latitude=35.0, longitude=139.0, region="東京都", timestamp=datetime.now(timezone.utc))
    actions = await on_new_earthquake(event)
    assert "large_earthquake_investigation" in actions

@pytest.mark.asyncio
async def test_small_earthquake_no_trigger(db_engine):
    event = EarthquakeEvent(event_id="small", magnitude=3.0, depth_km=10.0, latitude=35.0, longitude=139.0, region="東京都", timestamp=datetime.now(timezone.utc))
    actions = await on_new_earthquake(event)
    assert "large_earthquake_investigation" not in actions

@pytest.mark.asyncio
async def test_b_value_trigger(db_engine):
    await _seed_for_triggers()
    actions = await on_b_value_change("東京都", 1.0, 0.7)
    assert "b_value_investigation" in actions

@pytest.mark.asyncio
async def test_b_value_no_trigger(db_engine):
    actions = await on_b_value_change("東京都", 1.0, 0.95)
    assert actions == []
