"""統計分析 API エンドポイントのテスト。"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
import random

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_analysis_events(count: int = 50):
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(count):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=f"stat-{uuid.uuid4().hex[:8]}",
                source="p2p",
                magnitude=round(random.uniform(1.5, 6.5), 1),
                depth_km=round(random.uniform(5, 100), 1),
                latitude=35.0 + random.uniform(-2, 2),
                longitude=139.0 + random.uniform(-2, 2),
                region="東京都" if i % 3 != 0 else "大阪府",
                occurred_at=base_time + timedelta(days=random.uniform(0, 180)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_statistics(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/summary?region=東京都")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "magnitude_distribution" in data
    assert "depth_distribution" in data
    assert data["total_events"] > 0


@pytest.mark.asyncio
async def test_get_statistics_empty(async_client, db_engine):
    resp = await async_client.get("/statistics/summary?region=存在しない")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] == 0


@pytest.mark.asyncio
async def test_get_gutenberg_richter(async_client, db_engine):
    await _seed_analysis_events(100)
    resp = await async_client.get("/statistics/gutenberg-richter")
    assert resp.status_code == 200
    data = resp.json()
    assert "b_value" in data
    assert "a_value" in data
    assert "mc" in data


@pytest.mark.asyncio
async def test_get_b_value_timeseries(async_client, db_engine):
    await _seed_analysis_events(100)
    resp = await async_client.get("/statistics/b-value-timeseries?window_days=60&step_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeseries" in data
    assert isinstance(data["timeseries"], list)


@pytest.mark.asyncio
async def test_get_fractal_dimension(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/fractal-dimension")
    assert resp.status_code == 200
    data = resp.json()
    assert "d2" in data


@pytest.mark.asyncio
async def test_get_decluster(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/decluster")
    assert resp.status_code == 200
    data = resp.json()
    assert "n_total" in data
    assert "n_mainshocks" in data
    assert "n_aftershocks" in data
