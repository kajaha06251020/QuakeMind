"""event_store のテスト。"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.domain.models import EarthquakeEvent
from app.usecases.event_store import save_events
from app.infrastructure.models_db import EarthquakeEventDB
from sqlalchemy import select


@pytest.mark.asyncio
async def test_save_events_basic(db_session):
    events = [
        EarthquakeEvent(
            event_id="ev-001", magnitude=5.0, depth_km=10.0,
            latitude=35.0, longitude=139.0, region="東京都",
            timestamp=datetime.now(timezone.utc), source="p2p",
        ),
    ]
    count = await save_events(events)
    assert count == 1

    result = await db_session.execute(select(EarthquakeEventDB))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].event_id == "ev-001"


@pytest.mark.asyncio
async def test_save_events_duplicates_ignored(db_session):
    event = EarthquakeEvent(
        event_id="ev-dup", magnitude=5.0, depth_km=10.0,
        latitude=35.0, longitude=139.0, region="東京都",
        timestamp=datetime.now(timezone.utc), source="p2p",
    )
    count1 = await save_events([event])
    count2 = await save_events([event])
    assert count1 == 1
    assert count2 == 0


@pytest.mark.asyncio
async def test_save_events_empty_list(db_session):
    count = await save_events([])
    assert count == 0


@pytest.mark.asyncio
async def test_save_events_multiple(db_session):
    now = datetime.now(timezone.utc)
    events = [
        EarthquakeEvent(
            event_id=f"batch-{i}", magnitude=4.0 + i * 0.1, depth_km=20.0,
            latitude=35.0, longitude=139.0, region="テスト",
            timestamp=now, source="usgs",
        )
        for i in range(5)
    ]
    count = await save_events(events)
    assert count == 5
