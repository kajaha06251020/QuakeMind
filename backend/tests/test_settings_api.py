"""GET/PUT /settings エンドポイントのテスト。"""
import pytest


@pytest.mark.asyncio
async def test_get_settings_default(async_client, db_engine):
    """初回アクセスでデフォルト設定が自動作成される。"""
    resp = await async_client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_severity"] == "LOW"
    assert data["region_filters"] == []
    assert data["notification_channels"] == []


@pytest.mark.asyncio
async def test_put_settings(async_client, db_engine):
    """設定を更新できる。"""
    resp = await async_client.put("/settings", json={
        "min_severity": "HIGH",
        "region_filters": ["東京都", "大阪府"],
        "notification_channels": [{"type": "discord", "url": "https://example.com/webhook"}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_severity"] == "HIGH"
    assert data["region_filters"] == ["東京都", "大阪府"]
    assert len(data["notification_channels"]) == 1


@pytest.mark.asyncio
async def test_put_then_get_settings(async_client, db_engine):
    """PUT した設定が GET で取得できる。"""
    await async_client.put("/settings", json={
        "min_severity": "MEDIUM",
        "region_filters": ["宮城県"],
        "notification_channels": [],
    })
    resp = await async_client.get("/settings")
    data = resp.json()
    assert data["min_severity"] == "MEDIUM"
    assert data["region_filters"] == ["宮城県"]


@pytest.mark.asyncio
async def test_put_settings_invalid_severity(async_client, db_engine):
    """無効な severity は 422。"""
    resp = await async_client.put("/settings", json={
        "min_severity": "INVALID",
    })
    assert resp.status_code == 422
