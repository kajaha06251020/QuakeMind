"""データベースアクセスレイヤー（SQLAlchemy async）。"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import SeenEventDB, AlertDB, EarthquakeEventDB, UserSettingsDB
from app.domain.models import AlertMessage, RiskScore, EvacuationRoute

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """互換用: database.init_db() を呼ぶ。"""
    from app.infrastructure.database import init_db as _init
    await _init()


async def is_event_seen(event_id: str) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(SeenEventDB.event_id).where(SeenEventDB.event_id == event_id)
        )
        return result.scalar_one_or_none() is not None


async def mark_event_seen(event_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(
            select(SeenEventDB).where(SeenEventDB.event_id == event_id)
        )
        if existing.scalar_one_or_none() is None:
            session.add(SeenEventDB(
                event_id=event_id,
                seen_at=datetime.now(timezone.utc),
            ))
            await session.commit()


async def save_alert(
    alert: AlertMessage,
    risk: Optional[RiskScore] = None,
    route: Optional[EvacuationRoute] = None,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        # 既存アラートを削除（UPSERT の代替）
        await session.execute(
            delete(AlertDB).where(AlertDB.event_id == alert.event_id)
        )
        session.add(AlertDB(
            id=uuid.uuid4(),
            event_id=alert.event_id,
            severity=alert.severity,
            ja_text=alert.ja_text,
            en_text=alert.en_text,
            is_fallback=alert.is_fallback,
            created_at=alert.timestamp,
            risk_json=risk.model_dump() if risk else None,
            route_json=route.model_dump(mode="json") if route else None,
        ))
        await session.commit()


async def get_latest_alert() -> Optional[dict]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "event_id": row.event_id,
            "severity": row.severity,
            "ja_text": row.ja_text,
            "en_text": row.en_text,
            "is_fallback": row.is_fallback,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "risk_json": row.risk_json,
            "route_json": row.route_json,
        }


async def get_db_status() -> dict:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(AlertDB))
        total = result.scalar_one()
        latest = await get_latest_alert()
    return {"total_alerts": total, "latest": latest}


async def get_alert_locations(limit: int = 50) -> list[dict]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()

    locations = []
    for row in rows:
        route = row.route_json
        if not route:
            continue
        lat = route.get("latitude") if isinstance(route, dict) else None
        lon = route.get("longitude") if isinstance(route, dict) else None
        if lat is None or lon is None:
            continue
        locations.append({
            "event_id": row.event_id,
            "severity": row.severity,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "latitude": lat,
            "longitude": lon,
            "danger_radius_km": route.get("danger_radius_km"),
        })
    return locations


async def get_alerts(limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    factory = get_session_factory()
    async with factory() as session:
        total_result = await session.execute(select(func.count()).select_from(AlertDB))
        total = total_result.scalar_one()
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(limit).offset(offset)
        )
        rows = result.scalars().all()
    return [
        {
            "event_id": r.event_id,
            "severity": r.severity,
            "ja_text": r.ja_text,
            "en_text": r.en_text,
            "is_fallback": r.is_fallback,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ], total
