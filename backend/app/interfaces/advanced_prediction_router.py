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


@router.get("/fault-interactions")
async def fault_interactions(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.fault_graph import analyze_fault_interactions
    records = await _get_records(region, start, end)
    return analyze_fault_interactions(records)


@router.post("/analyze-waveform")
async def analyze_waveform_endpoint(data: dict):
    from app.usecases.phase_detection import analyze_waveform
    import numpy as np
    waveform = np.array(data.get("waveform", []))
    sr = data.get("sampling_rate", 100.0)
    if len(waveform) < 100:
        return {"error": "波形データが短すぎます（最低100サンプル）"}
    return analyze_waveform(waveform, sr)


@router.get("/self-improvement")
async def self_improvement_status():
    from app.services.self_improvement import get_improvement_summary
    return get_improvement_summary()


@router.post("/self-improvement/verify")
async def self_improvement_verify(model_name: str, predicted_prob: float, actual_occurred: bool):
    from app.services.self_improvement import verify_and_update
    return await verify_and_update(model_name, predicted_prob, actual_occurred)


@router.get("/domain-similarity")
async def domain_similarity(region: Optional[str] = None):
    from app.usecases.transfer_learning import extract_transfer_features, compute_domain_similarity
    all_records = await _get_records()
    region_records = await _get_records(region=region) if region else all_records
    source = extract_transfer_features(all_records)
    target = extract_transfer_features(region_records)
    return compute_domain_similarity(source, target)
