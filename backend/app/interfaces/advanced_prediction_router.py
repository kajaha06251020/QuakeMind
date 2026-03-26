"""最先端予測 API ルーター (Tier 1)"""
from typing import Optional
from fastapi import APIRouter, Query
from app.infrastructure import db

router = APIRouter(prefix="/advanced-prediction", tags=["advanced-prediction"])


async def _get_records(region=None, start=None, end=None):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/bayesian-etas")
async def bayesian_etas(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    hours: int = Query(default=72, ge=1, le=720),
    n_samples: int = Query(default=200, ge=50, le=2000),
):
    from app.usecases.bayesian_etas import bayesian_etas_forecast
    records = await _get_records(region, start, end)
    return bayesian_etas_forecast(records, forecast_hours=hours, n_samples=n_samples, burn_in=max(50, n_samples // 5))


@router.get("/coulomb-rate-state")
async def coulomb_rs(
    delta_cfs_mpa: float = Query(...),
    background_rate: float = Query(default=0.5),
    forecast_days: float = Query(default=30),
):
    from app.usecases.coulomb_rate_state import rate_state_forecast
    return rate_state_forecast(background_rate, delta_cfs_mpa, forecast_days)


@router.get("/changepoints")
async def changepoints(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    window_days: int = Query(default=7, ge=3, le=30),
):
    from app.usecases.changepoint import detect_rate_changepoints
    records = await _get_records(region, start, end)
    return detect_rate_changepoints(records, window_days=window_days)


@router.get("/ensemble")
async def ensemble_predict(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    """マルチモデルアンサンブル（BMA）予測。"""
    from app.usecases.etas import etas_forecast
    from app.usecases.ml_predictor import predict_large_earthquake
    from app.usecases.ensemble import bayesian_model_averaging

    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}

    etas = etas_forecast(records, forecast_hours=72)
    ml = predict_large_earthquake(records)

    preds = [
        {"name": "etas", "probability": min(1, etas.get("probability_m4_plus", 0)), "weight": 2.0, "uncertainty": 0.15},
        {"name": "ml", "probability": min(1, ml.get("probability", 0)), "weight": 1.0, "uncertainty": 0.2},
    ]
    return bayesian_model_averaging(preds)


@router.get("/oef-forecast")
async def oef_forecast(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    magnitude_threshold: float = Query(default=5.0, ge=3.0, le=9.0),
):
    """Operational Earthquake Forecasting — 24h/7d/30d 確率予報。"""
    from app.usecases.oef import generate_oef_forecast
    records = await _get_records(region, start, end)
    return await generate_oef_forecast(records, magnitude_threshold=magnitude_threshold)
