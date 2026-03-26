"""仮説エンジン。異常検出時に自動で仮説を生成し、時間経過で検証する。"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import HypothesisDB

logger = logging.getLogger(__name__)


async def create_hypothesis(
    title: str,
    description: str,
    region: str | None = None,
    trigger_event: str | None = None,
    verify_after_days: int = 30,
    evidence: list | None = None,
) -> str:
    """仮説を作成する。"""
    hyp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    factory = get_session_factory()
    async with factory() as session:
        session.add(HypothesisDB(
            id=hyp_id,
            title=title,
            description=description,
            region=region,
            status="monitoring",
            evidence_json=evidence or [],
            trigger_event=trigger_event,
            verify_after_days=verify_after_days,
            created_at=now,
            updated_at=now,
        ))
        await session.commit()
    logger.info("[Hypothesis] 作成: %s", title)
    return str(hyp_id)


async def update_hypothesis(hyp_id: str, status: str, new_evidence: dict | None = None) -> dict | None:
    """仮説のステータスを更新する。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(HypothesisDB).where(HypothesisDB.id == uuid.UUID(hyp_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        row.status = status
        row.updated_at = datetime.now(timezone.utc)
        if status in ("confirmed", "rejected", "expired"):
            row.resolved_at = datetime.now(timezone.utc)
        if new_evidence:
            evidence = row.evidence_json or []
            evidence.append(new_evidence)
            row.evidence_json = evidence
        await session.commit()
        await session.refresh(row)
    return _to_dict(row)


async def get_active_hypotheses() -> list[dict]:
    """監視中の仮説を取得する。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(HypothesisDB).where(HypothesisDB.status == "monitoring")
            .order_by(HypothesisDB.created_at.desc())
        )
        rows = result.scalars().all()
    return [_to_dict(r) for r in rows]


async def check_expired_hypotheses() -> int:
    """期限切れの仮説を expired に更新する。"""
    now = datetime.now(timezone.utc)
    factory = get_session_factory()
    count = 0
    async with factory() as session:
        result = await session.execute(
            select(HypothesisDB).where(HypothesisDB.status == "monitoring")
        )
        for row in result.scalars().all():
            created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
            deadline = created + timedelta(days=row.verify_after_days)
            if now > deadline:
                row.status = "expired"
                row.resolved_at = now
                row.updated_at = now
                count += 1
        await session.commit()
    if count > 0:
        logger.info("[Hypothesis] %d 件の仮説が期限切れ", count)
    return count


def _to_dict(row: HypothesisDB) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "region": row.region,
        "status": row.status,
        "evidence": row.evidence_json,
        "trigger_event": row.trigger_event,
        "verify_after_days": row.verify_after_days,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }
