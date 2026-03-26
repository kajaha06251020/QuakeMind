"""ヘルスチェックのテスト。"""
import pytest
from unittest.mock import patch
from app.services.health import check_health


@pytest.mark.asyncio
async def test_health_all_healthy(db_engine, httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)
    with patch("app.services.health.get_source_status", return_value={
        "p2p": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": None},
        "usgs": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": None},
    }):
        result = await check_health()
    assert result["status"] == "healthy"
    assert result["components"]["database"]["status"] == "healthy"
    assert result["components"]["llm_server"]["status"] == "healthy"
    assert result["components"]["data_sources"]["p2p"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_llm_down(db_engine, httpx_mock):
    import httpx
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with patch("app.services.health.get_source_status", return_value={}):
        result = await check_health()
    assert result["status"] == "degraded"
    assert result["components"]["llm_server"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_source_has_error(db_engine, httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)
    with patch("app.services.health.get_source_status", return_value={
        "p2p": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": "timeout"},
    }):
        result = await check_health()
    assert result["components"]["data_sources"]["p2p"]["status"] == "unhealthy"
    assert result["components"]["data_sources"]["p2p"]["last_error"] == "timeout"
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_claude_provider(db_engine):
    with (
        patch("app.services.health.settings") as mock_settings,
        patch("app.services.health.get_source_status", return_value={}),
    ):
        mock_settings.llm_provider = "claude"
        mock_settings.local_llm_base_url = "http://127.0.0.1:8081"
        mock_settings.database_url = "sqlite+aiosqlite://"
        mock_settings.usgs_enabled = True
        mock_settings.jma_xml_enabled = False
        result = await check_health()
    assert result["components"]["llm_server"]["status"] == "skipped"
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_uptime(db_engine, httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)
    with patch("app.services.health.get_source_status", return_value={}):
        result = await check_health()
    assert "uptime_seconds" in result
    assert "started_at" in result
    assert result["uptime_seconds"] >= 0
