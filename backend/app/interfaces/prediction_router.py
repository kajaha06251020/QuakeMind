"""予測モデル API ルーター (Phase C3)"""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.infrastructure import db
from app.usecases.etas import etas_forecast
from app.usecases.coulomb import compute_coulomb_stress
from app.usecases.foreshock_matcher import match_foreshock_pattern
from app.usecases.chain_probability import compute_chain_probability
from app.usecases.timeseries_forecast import forecast_daily_counts
from app.usecases.ml_predictor import predict_large_earthquake
from app.usecases.focal_mechanism import classify_fault_type, estimate_rupture_area
from app.usecases.risk_profile import compute_risk_profile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prediction", tags=["prediction"])


async def _get_records(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/etas-forecast")
async def get_etas_forecast(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    hours: int = Query(default=72, ge=1, le=720),
):
    records = await _get_records(region=region, start=start, end=end)
    return etas_forecast(records, forecast_hours=hours)


@router.get("/coulomb-stress")
async def get_coulomb_stress(
    source_lat: float = Query(...),
    source_lon: float = Query(...),
    source_magnitude: float = Query(...),
    source_depth_km: float = Query(default=10.0),
    grid_spacing_deg: float = Query(default=0.5),
    grid_radius_deg: float = Query(default=2.0),
):
    return compute_coulomb_stress(
        source_lat=source_lat, source_lon=source_lon,
        source_depth_km=source_depth_km, source_magnitude=source_magnitude,
        grid_spacing_deg=grid_spacing_deg, grid_radius_deg=grid_radius_deg,
    )


@router.get("/foreshock-match")
async def get_foreshock_match(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    window_days: int = Query(default=30, ge=7, le=90),
):
    records = await _get_records(region=region, start=start, end=end)
    return match_foreshock_pattern(records, window_days=window_days)


@router.get("/chain-probability")
async def get_chain_probability(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
    grid_spacing_deg: float = Query(default=0.5),
    grid_radius_deg: float = Query(default=2.0),
):
    records = await _get_records(region=region, start=start, end=end)
    return compute_chain_probability(
        records, forecast_hours=hours,
        grid_spacing_deg=grid_spacing_deg, grid_radius_deg=grid_radius_deg,
    )


@router.get("/timeseries-forecast")
async def get_timeseries_forecast(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    forecast_days: int = Query(default=7, ge=1, le=30),
):
    records = await _get_records(region=region, start=start, end=end)
    return forecast_daily_counts(records, forecast_days=forecast_days)


@router.get("/etas-parameters")
async def get_etas_parameters(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    from app.usecases.etas_mle import estimate_etas_parameters
    records = await _get_records(region=region, start=start, end=end)
    return estimate_etas_parameters(records)


@router.get("/ml-predict")
async def ml_predict(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    magnitude_threshold: float = Query(default=5.0),
):
    records = await _get_records(region=region, start=start, end=end)
    return predict_large_earthquake(records, magnitude_threshold)


@router.get("/focal-mechanism")
async def focal_mechanism(
    magnitude: float = Query(...),
    rake: float = Query(default=0),
):
    return {"fault_type": classify_fault_type(rake), "rupture": estimate_rupture_area(magnitude)}


@router.get("/risk-profile")
async def risk_profile(
    region: str = Query(...),
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    records = await _get_records(region=region, start=start, end=end)
    return compute_risk_profile(region, records)
