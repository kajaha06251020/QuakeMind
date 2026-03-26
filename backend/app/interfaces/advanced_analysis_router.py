"""高度分析 API ルーター (Phase C2)"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.infrastructure import db
from app.usecases.clustering import detect_clusters
from app.usecases.anomaly_detection import detect_anomaly, detect_quiescence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis-advanced", tags=["advanced-analysis"])


async def _get_records(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/clusters")
async def get_clusters(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    spatial_km: float = Query(default=50.0, ge=5.0, le=500.0),
    temporal_days: float = Query(default=7.0, ge=1.0, le=90.0),
    min_samples: int = Query(default=3, ge=2, le=20),
):
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < min_samples:
        return {"n_clusters": 0, "noise_events": len(records), "clusters": []}
    return detect_clusters(records, spatial_km=spatial_km, temporal_days=temporal_days, min_samples=min_samples)


@router.get("/anomaly")
async def get_anomaly(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    evaluation_days: int = Query(default=7, ge=1, le=90),
):
    records = await _get_records(region=region, start=start, end=end)
    result = detect_anomaly(records, evaluation_days=evaluation_days)
    result["region"] = region
    return result


@router.get("/quiescence")
async def get_quiescence(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    evaluation_days: int = Query(default=30, ge=7, le=365),
):
    records = await _get_records(region=region, start=start, end=end)
    result = detect_quiescence(records, evaluation_days=evaluation_days)
    result["region"] = region
    return result
