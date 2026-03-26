"""database.py + models_db.py のテスト。"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.infrastructure.models_db import Base, EarthquakeEventDB, AlertDB, SeenEventDB, UserSettingsDB


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys = ON"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_earthquake_event(session: AsyncSession):
    event = EarthquakeEventDB(
        id=uuid.uuid4(),
        event_id="test-001",
        source="p2p",
        magnitude=5.0,
        depth_km=10.0,
        latitude=35.68,
        longitude=139.76,
        region="東京都",
        occurred_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.commit()

    result = await session.execute(select(EarthquakeEventDB).where(EarthquakeEventDB.event_id == "test-001"))
    row = result.scalar_one()
    assert row.magnitude == 5.0
    assert row.region == "東京都"


@pytest.mark.asyncio
async def test_earthquake_event_unique_constraint(session: AsyncSession):
    from sqlalchemy.exc import IntegrityError
    now = datetime.now(timezone.utc)
    for _ in range(2):
        session.add(EarthquakeEventDB(
            id=uuid.uuid4(), event_id="dup-001", source="p2p",
            magnitude=5.0, depth_km=10.0, latitude=35.0, longitude=139.0,
            region="テスト", occurred_at=now, fetched_at=now,
        ))
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_create_alert_with_fk(session: AsyncSession):
    now = datetime.now(timezone.utc)
    event = EarthquakeEventDB(
        id=uuid.uuid4(), event_id="ev-001", source="usgs",
        magnitude=6.0, depth_km=30.0, latitude=35.0, longitude=139.0,
        region="大阪府", occurred_at=now, fetched_at=now,
    )
    session.add(event)
    await session.flush()
    alert = AlertDB(
        id=uuid.uuid4(), event_id="ev-001", severity="HIGH",
        ja_text="テスト", en_text="Test", is_fallback=False,
        risk_json=None, route_json=None, created_at=now,
    )
    session.add(alert)
    await session.commit()
    result = await session.execute(select(AlertDB).where(AlertDB.event_id == "ev-001"))
    row = result.scalar_one()
    assert row.severity == "HIGH"


@pytest.mark.asyncio
async def test_create_user_settings(session: AsyncSession):
    now = datetime.now(timezone.utc)
    settings = UserSettingsDB(
        id=uuid.uuid4(), user_id="default",
        min_severity="LOW", region_filters=[], notification_channels=[],
        created_at=now, updated_at=now,
    )
    session.add(settings)
    await session.commit()
    result = await session.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == "default"))
    row = result.scalar_one()
    assert row.min_severity == "LOW"
