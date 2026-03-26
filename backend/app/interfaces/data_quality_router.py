"""データ品質 API ルーター (Phase C6)"""
from typing import Optional
from fastapi import APIRouter, Query
from app.infrastructure import db
from app.usecases.data_quality import score_data_sources
from app.usecases.multi_source_locate import locate_multi_source

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/scores")
async def get_quality_scores():
    return score_data_sources()


@router.get("/multi-source-locate")
async def get_multi_source_locate(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(region=region, start=start_dt, end=end_dt)
    return {"merged_events": locate_multi_source(records)}
