"""実験ログ。どのパラメータでどの分析を実行し何が得られたかを記録する。"""
import uuid
import time
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sqlalchemy import select, func

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import ExperimentLogDB

logger = logging.getLogger(__name__)


@asynccontextmanager
async def track_experiment(name: str, parameters: dict | None = None):
    """実験をコンテキストマネージャで追跡する。

    Usage:
        async with track_experiment("etas_mle", {"region": "東京都"}) as exp:
            result = await some_analysis()
            exp["results"] = result
    """
    entry = {"results": None}
    start = time.monotonic()
    status = "completed"

    try:
        yield entry
    except Exception as e:
        status = "failed"
        entry["results"] = {"error": str(e)}
        raise
    finally:
        duration = time.monotonic() - start
        await log_experiment(name, parameters, entry.get("results"), duration, status)


async def log_experiment(
    name: str,
    parameters: dict | None = None,
    results: dict | None = None,
    duration_seconds: float | None = None,
    status: str = "completed",
) -> str:
    """実験ログを記録する。"""
    exp_id = uuid.uuid4()
    factory = get_session_factory()
    async with factory() as session:
        session.add(ExperimentLogDB(
            id=exp_id,
            experiment_name=name,
            parameters_json=parameters,
            results_json=results,
            duration_seconds=duration_seconds,
            status=status,
            created_at=datetime.now(timezone.utc),
        ))
        await session.commit()
    return str(exp_id)


async def get_experiment_logs(
    name: str | None = None,
    limit: int = 50,
) -> list[dict]:
    factory = get_session_factory()
    async with factory() as session:
        query = select(ExperimentLogDB)
        if name:
            query = query.where(ExperimentLogDB.experiment_name == name)
        result = await session.execute(
            query.order_by(ExperimentLogDB.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "experiment_name": r.experiment_name,
            "parameters": r.parameters_json,
            "results": r.results_json,
            "duration_seconds": r.duration_seconds,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
