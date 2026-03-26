"""研究ジャーナル。発見・異常・レポートを自動記録する。"""
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import ResearchJournalDB

logger = logging.getLogger(__name__)


async def add_entry(
    entry_type: str,
    title: str,
    content: str,
    region: str | None = None,
    metadata: dict | None = None,
) -> str:
    """ジャーナルエントリを追加する。entry_id を返す。"""
    entry_id = uuid.uuid4()
    factory = get_session_factory()
    async with factory() as session:
        session.add(ResearchJournalDB(
            id=entry_id,
            entry_type=entry_type,
            title=title,
            content=content,
            region=region,
            metadata_json=metadata,
            created_at=datetime.now(timezone.utc),
        ))
        await session.commit()
    logger.info("[Journal] %s: %s", entry_type, title)
    return str(entry_id)


async def get_entries(
    entry_type: str | None = None,
    region: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """ジャーナルエントリを取得する。"""
    factory = get_session_factory()
    async with factory() as session:
        query = select(ResearchJournalDB)
        count_query = select(func.count()).select_from(ResearchJournalDB)

        if entry_type:
            query = query.where(ResearchJournalDB.entry_type == entry_type)
            count_query = count_query.where(ResearchJournalDB.entry_type == entry_type)
        if region:
            query = query.where(ResearchJournalDB.region == region)
            count_query = count_query.where(ResearchJournalDB.region == region)

        total = (await session.execute(count_query)).scalar_one()
        rows = (await session.execute(
            query.order_by(ResearchJournalDB.created_at.desc()).limit(limit).offset(offset)
        )).scalars().all()

    return [
        {
            "id": str(r.id),
            "entry_type": r.entry_type,
            "title": r.title,
            "content": r.content,
            "region": r.region,
            "metadata": r.metadata_json,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ], total
