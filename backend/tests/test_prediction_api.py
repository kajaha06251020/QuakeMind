"""予測モデル API のテスト。"""
import uuid
import pytest
import random
from datetime import datetime, timezone, timedelta

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_prediction_events():
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(30):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"pred-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 6.0), 1),
                depth_km=round(random.uniform(5, 50), 1),
                latitude=35.0 + random.uniform(-1, 1),
                longitude=139.0 + random.uniform(-1, 1),
                region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 25)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_etas_forecast(async_client, db_engine):
    await _seed_prediction_events()
    resp = await async_client.get("/prediction/etas-forecast?hours=72")
    assert resp.status_code == 200
    data = resp.json()
    assert "expected_events" in data
    assert "probability_m4_plus" in data


@pytest.mark.asyncio
async def test_coulomb_stress(async_client, db_engine):
    await _seed_prediction_events()
    resp = await async_client.get("/prediction/coulomb-stress?source_lat=35.0&source_lon=139.0&source_magnitude=6.0&source_depth_km=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert "stress_changes" in data


@pytest.mark.asyncio
async def test_foreshock_match(async_client, db_engine):
    await _seed_prediction_events()
    resp = await async_client.get("/prediction/foreshock-match")
    assert resp.status_code == 200
    data = resp.json()
    assert "similarity_score" in data
    assert "alert_level" in data


@pytest.mark.asyncio
async def test_chain_probability(async_client, db_engine):
    await _seed_prediction_events()
    resp = await async_client.get("/prediction/chain-probability?hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert "grid" in data


@pytest.mark.asyncio
async def test_timeseries_forecast(async_client, db_engine):
    await _seed_prediction_events()
    resp = await async_client.get("/prediction/timeseries-forecast?forecast_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "forecast" in data
