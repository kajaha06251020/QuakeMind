"""ヘルスチェックロジック。"""
import time
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from app.config import settings
from app.infrastructure.database import get_session_factory
from app.infrastructure.multi_source import get_source_status

logger = logging.getLogger(__name__)

_started_at: datetime = datetime.now(timezone.utc)
_start_time: float = time.monotonic()


def set_started_at() -> None:
    global _started_at, _start_time
    _started_at = datetime.now(timezone.utc)
    _start_time = time.monotonic()


async def _check_database() -> dict:
    try:
        factory = get_session_factory()
        start = time.monotonic()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000, 1)
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        logger.warning("[Health] DB チェック失敗: %s", e)
        return {"status": "unhealthy", "error": str(e)}


async def _check_llm_server() -> dict:
    if settings.llm_provider != "local":
        return {"status": "skipped", "provider": settings.llm_provider}
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.local_llm_base_url}/health")
            resp.raise_for_status()
        latency = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "healthy",
            "provider": "local",
            "base_url": settings.local_llm_base_url,
            "latency_ms": latency,
        }
    except Exception as e:
        logger.warning("[Health] LLM チェック失敗: %s", e)
        return {
            "status": "unhealthy",
            "provider": "local",
            "base_url": settings.local_llm_base_url,
            "error": str(e),
        }


def _check_data_sources() -> dict:
    raw = get_source_status()
    known_sources = {
        "p2p": True,
        "usgs": settings.usgs_enabled,
        "jma_xml": settings.jma_xml_enabled,
    }
    result = {}
    for name, enabled in known_sources.items():
        if not enabled and name not in raw:
            result[name] = {"status": "disabled", "last_fetch_at": None, "last_error": None}
        elif name in raw:
            entry = raw[name]
            status = "healthy" if entry.get("last_error") is None else "unhealthy"
            result[name] = {
                "status": status,
                "last_fetch_at": entry.get("last_fetch_at"),
                "last_error": entry.get("last_error"),
            }
        else:
            result[name] = {"status": "unknown", "last_fetch_at": None, "last_error": None}
    return result


async def check_health() -> dict:
    db_status = await _check_database()
    llm_status = await _check_llm_server()
    source_status = _check_data_sources()

    all_statuses = [db_status["status"]]
    if llm_status["status"] not in ("skipped",):
        all_statuses.append(llm_status["status"])
    all_statuses.extend(
        s["status"] for s in source_status.values()
        if s["status"] not in ("disabled", "unknown")
    )
    overall = "healthy" if all(s == "healthy" for s in all_statuses) else "degraded"

    return {
        "status": overall,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "started_at": _started_at.isoformat(),
        "components": {
            "database": db_status,
            "llm_server": llm_status,
            "data_sources": source_status,
        },
    }
