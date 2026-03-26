import pytest

@pytest.mark.asyncio
async def test_shakemap_api(async_client, db_engine):
    resp = await async_client.get("/realtime/shakemap?lat=35.0&lon=139.0&magnitude=6.5")
    assert resp.status_code == 200
    assert "grid" in resp.json()

@pytest.mark.asyncio
async def test_tsunami_api(async_client, db_engine):
    resp = await async_client.get("/realtime/tsunami-arrival?lat=38.0&lon=142.0&magnitude=7.5&depth_km=20.0")
    assert resp.status_code == 200
    assert "arrivals" in resp.json()

@pytest.mark.asyncio
async def test_damage_api(async_client, db_engine):
    resp = await async_client.get("/realtime/damage-estimate?lat=35.5&lon=139.5&magnitude=7.0")
    assert resp.status_code == 200
    assert "damage_level" in resp.json()
