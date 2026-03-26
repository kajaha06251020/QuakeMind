"""
統計分析 API ルーター (Phase C1)

GET ベースのエンドポイント。earthquake_events テーブルのデータを使用。
"""
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.infrastructure import db
from app.usecases.seismic_analysis import (
    analyze_gutenberg_richter,
    decluster_gardner_knopoff,
)
from app.usecases.fractal import compute_correlation_dimension
from app.usecases.b_value_tracker import compute_b_value_timeseries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/statistics", tags=["statistics"])


async def _get_records(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    min_magnitude: Optional[float] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(
        region=region, start=start_dt, end=end_dt, min_magnitude=min_magnitude,
    )
    return records


@router.get("/summary")
async def get_statistics(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    records = await _get_records(region=region, start=start, end=end)
    if not records:
        return {
            "region": region,
            "total_events": 0,
            "magnitude_distribution": None,
            "depth_distribution": None,
            "frequency_by_magnitude_bin": {},
        }

    mags = np.array([r.magnitude for r in records])
    depths = np.array([r.depth_km for r in records])

    bins = np.arange(np.floor(mags.min()), np.ceil(mags.max()) + 1, 1.0)
    freq_by_bin = {}
    for b in bins:
        count = int(np.sum((mags >= b) & (mags < b + 1)))
        if count > 0:
            freq_by_bin[str(float(b))] = count

    return {
        "region": region,
        "total_events": len(records),
        "magnitude_distribution": {
            "min": round(float(mags.min()), 1),
            "max": round(float(mags.max()), 1),
            "mean": round(float(mags.mean()), 2),
            "median": round(float(np.median(mags)), 2),
        },
        "depth_distribution": {
            "min": round(float(depths.min()), 1),
            "max": round(float(depths.max()), 1),
            "mean": round(float(depths.mean()), 2),
            "median": round(float(np.median(depths)), 2),
        },
        "frequency_by_magnitude_bin": freq_by_bin,
    }


@router.get("/gutenberg-richter")
async def get_gutenberg_richter(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    mc_method: str = Query(default="MBS-WW"),
):
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 10:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低10必要)")
    try:
        result = analyze_gutenberg_richter(records, mc_method=mc_method)
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/b-value-timeseries")
async def get_b_value_timeseries(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    window_days: int = Query(default=90, ge=30, le=365),
    step_days: int = Query(default=30, ge=7, le=180),
):
    records = await _get_records(region=region, start=start, end=end)
    timeseries = compute_b_value_timeseries(records, window_days=window_days, step_days=step_days)
    return {
        "region": region,
        "window_days": window_days,
        "step_days": step_days,
        "timeseries": timeseries,
    }


@router.get("/fractal-dimension")
async def get_fractal_dimension(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 10:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低10必要)")

    lats = np.array([r.latitude for r in records])
    lons = np.array([r.longitude for r in records])
    d2 = compute_correlation_dimension(lats, lons)

    interpretation = ""
    if d2 is not None:
        if d2 < 1.5:
            interpretation = "空間的に強く集中（応力集中の可能性）"
        elif d2 < 2.0:
            interpretation = "やや集中的な分布"
        else:
            interpretation = "広く分散した分布"

    return {
        "region": region,
        "d2": d2,
        "n_events": len(records),
        "interpretation": interpretation,
    }


@router.get("/decluster")
async def get_decluster(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 2:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低2必要)")

    result = decluster_gardner_knopoff(records)
    return {
        "method": result.method,
        "n_total": result.n_total,
        "n_mainshocks": result.n_mainshocks,
        "n_aftershocks": result.n_aftershocks,
        "aftershock_ratio": round(result.aftershock_ratio, 4),
    }
