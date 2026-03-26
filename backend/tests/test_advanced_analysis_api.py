"""高度分析 API のテスト。"""
import uuid
import pytest
import random
from datetime import datetime, timezone, timedelta

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_cluster_events():
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # クラスタ1: 近い場所・時間に集中
        for i in range(10):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"cl-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 5.0), 1),
                depth_km=20.0, latitude=35.0 + random.uniform(-0.05, 0.05),
                longitude=139.0 + random.uniform(-0.05, 0.05),
                region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 3)),
                fetched_at=datetime.now(timezone.utc),
            ))
        # 散在イベント
        for i in range(20):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"sc-{uuid.uuid4().hex[:8]}",
                source="usgs", magnitude=round(random.uniform(2.0, 4.0), 1),
                depth_km=30.0, latitude=30.0 + random.uniform(0, 10),
                longitude=130.0 + random.uniform(0, 10),
                region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 60)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_clusters(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert "n_clusters" in data
    assert "clusters" in data
    assert isinstance(data["clusters"], list)


@pytest.mark.asyncio
async def test_get_anomaly(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/anomaly?evaluation_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_anomalous" in data
    assert "background_rate" in data
    assert "p_value" in data


@pytest.mark.asyncio
async def test_get_quiescence(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/quiescence?evaluation_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_quiescent" in data
    assert "ratio" in data
