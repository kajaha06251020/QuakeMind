"""地震イベントの全件保存。magnitude_threshold 以下も含む。"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.domain.models import EarthquakeEvent
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

logger = logging.getLogger(__name__)


async def save_events(events: list[EarthquakeEvent]) -> int:
    """イベントを earthquake_events に一括保存する。
    event_id が既に存在する場合は無視。
    戻り値: 新規保存した件数。
    """
    if not events:
        return 0

    factory = get_session_factory()
    saved = 0
    async with factory() as session:
        for event in events:
            existing = await session.execute(
                select(EarthquakeEventDB.event_id).where(
                    EarthquakeEventDB.event_id == event.event_id
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=event.event_id,
                source=event.source,
                magnitude=event.magnitude,
                depth_km=event.depth_km,
                latitude=event.latitude,
                longitude=event.longitude,
                region=event.region,
                occurred_at=event.timestamp,
                fetched_at=datetime.now(timezone.utc),
            ))
            saved += 1
        await session.commit()

    if saved > 0:
        logger.info("[EventStore] %d 件保存（%d 件中）", saved, len(events))
    return saved
