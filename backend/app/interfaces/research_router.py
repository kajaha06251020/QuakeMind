"""AI解釈 API ルーター (Phase C5)"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.infrastructure import db
from app.usecases.research import generate_research_report
from app.usecases.briefing import generate_daily_briefing
from app.usecases.similar_search import find_similar_events

router = APIRouter(prefix="/research", tags=["research"])


async def _get_records(region=None, start=None, end=None):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/report")
async def get_research_report(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    records = await _get_records(region, start, end)
    return await generate_research_report(records)


@router.get("/briefing")
async def get_briefing(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, days: int = Query(default=1, ge=1, le=30)):
    records = await _get_records(region, start, end)
    return generate_daily_briefing(records, days=days)


@router.get("/similar")
async def get_similar(event_id: str = Query(...), region: Optional[str] = None):
    records = await _get_records(region=region)
    target = next((r for r in records if r.event_id == event_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"イベント {event_id} が見つかりません")
    results = find_similar_events(target, records)
    return {"target_event_id": event_id, "similar_events": results}
