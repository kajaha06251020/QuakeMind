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


async def get_events(
    limit: int = 50,
    offset: int = 0,
    min_magnitude: float | None = None,
    region: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[list[dict], int]:
    """イベント履歴を検索する。(events, total) を返す。"""
    factory = get_session_factory()
    async with factory() as session:
        query = select(EarthquakeEventDB)
        count_query = select(func.count()).select_from(EarthquakeEventDB)

        if min_magnitude is not None:
            query = query.where(EarthquakeEventDB.magnitude >= min_magnitude)
            count_query = count_query.where(EarthquakeEventDB.magnitude >= min_magnitude)
        if region is not None:
            query = query.where(EarthquakeEventDB.region == region)
            count_query = count_query.where(EarthquakeEventDB.region == region)
        if start is not None:
            query = query.where(EarthquakeEventDB.occurred_at >= start)
            count_query = count_query.where(EarthquakeEventDB.occurred_at >= start)
        if end is not None:
            query = query.where(EarthquakeEventDB.occurred_at <= end)
            count_query = count_query.where(EarthquakeEventDB.occurred_at <= end)

        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(EarthquakeEventDB.occurred_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        {
            "event_id": r.event_id,
            "source": r.source,
            "magnitude": r.magnitude,
            "depth_km": r.depth_km,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "region": r.region,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ], total


async def get_user_settings(user_id: str = "default") -> dict:
    """ユーザー設定を取得する。存在しなければデフォルトで自動作成。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettingsDB).where(UserSettingsDB.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            now = datetime.now(timezone.utc)
            row = UserSettingsDB(
                id=uuid.uuid4(), user_id=user_id,
                min_severity="LOW", region_filters=[], notification_channels=[],
                created_at=now, updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "min_severity": row.min_severity,
            "region_filters": row.region_filters or [],
            "notification_channels": row.notification_channels or [],
        }


async def update_user_settings(
    user_id: str = "default",
    min_severity: str | None = None,
    region_filters: list | None = None,
    notification_channels: list | None = None,
) -> dict:
    """ユーザー設定を更新する。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettingsDB).where(UserSettingsDB.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row is None:
            row = UserSettingsDB(
                id=uuid.uuid4(), user_id=user_id,
                min_severity=min_severity or "LOW",
                region_filters=region_filters or [],
                notification_channels=notification_channels or [],
                created_at=now, updated_at=now,
            )
            session.add(row)
        else:
            if min_severity is not None:
                row.min_severity = min_severity
            if region_filters is not None:
                row.region_filters = region_filters
            if notification_channels is not None:
                row.notification_channels = notification_channels
            row.updated_at = now
        await session.commit()
        await session.refresh(row)
    return {
        "min_severity": row.min_severity,
        "region_filters": row.region_filters or [],
        "notification_channels": row.notification_channels or [],
    }
