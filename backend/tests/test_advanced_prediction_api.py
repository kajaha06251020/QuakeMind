import pytest, uuid, random
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

async def _seed(n=40):
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(n):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"adv-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 6.0), 1),
                depth_km=20.0, latitude=35.0 + random.uniform(-1, 1),
                longitude=139.0 + random.uniform(-1, 1), region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 90)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()

@pytest.mark.asyncio
async def test_bayesian_etas_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/advanced-prediction/bayesian-etas?n_samples=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "expected_events" in data or "error" in data

@pytest.mark.asyncio
async def test_coulomb_rs_api(async_client, db_engine):
    resp = await async_client.get("/advanced-prediction/coulomb-rate-state?delta_cfs_mpa=0.01")
    assert resp.status_code == 200
    assert "rate_change_factor" in resp.json()

@pytest.mark.asyncio
async def test_changepoints_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/advanced-prediction/changepoints")
    assert resp.status_code == 200
    assert "changepoints" in resp.json()

@pytest.mark.asyncio
async def test_ensemble_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/advanced-prediction/ensemble")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_oef_api(async_client, db_engine):
    await _seed()
    resp = await async_client.get("/advanced-prediction/oef-forecast")
    assert resp.status_code == 200
