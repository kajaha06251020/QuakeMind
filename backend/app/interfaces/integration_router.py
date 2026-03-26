"""統合分析 API ルーター。全システムを横断する統合機能。"""
from typing import Optional
from fastapi import APIRouter, Query
from app.infrastructure import db

router = APIRouter(prefix="/integration", tags=["integration"])


async def _get_records(region=None, start=None, end=None):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/unified-probability")
async def unified_prob(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.bayesian_network import unified_probability
    from app.usecases.anomaly_detection import detect_anomaly
    from app.usecases.clustering import detect_clusters
    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}
    analysis = {}
    anomaly = detect_anomaly(records, evaluation_days=7)
    analysis["anomaly_detected"] = anomaly.get("is_anomalous", False)
    analysis["p_value"] = anomaly.get("p_value", 1.0)
    clusters = detect_clusters(records)
    analysis["n_clusters"] = clusters["n_clusters"]
    return unified_probability(analysis)


@router.get("/scenario")
async def scenario(lat: float = Query(...), lon: float = Query(...), magnitude: float = Query(...), depth_km: float = Query(default=15)):
    from app.usecases.scenario_engine import simulate_scenario
    return simulate_scenario(lat, lon, magnitude, depth_km)


@router.get("/scenario/preset")
async def preset_scenario(key: str = Query(...)):
    from app.usecases.scenario_engine import run_preset_scenario
    return run_preset_scenario(key)


@router.get("/decision-support")
async def decision(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.bayesian_network import unified_probability
    from app.usecases.anomaly_detection import detect_anomaly
    from app.usecases.clustering import detect_clusters
    from app.services.decision_support import generate_recommendations
    records = await _get_records(region, start, end)
    if len(records) < 10:
        return generate_recommendations("normal", 0.0, region=region)
    analysis = {}
    anomaly = detect_anomaly(records, evaluation_days=7)
    analysis["anomaly_detected"] = anomaly.get("is_anomalous", False)
    analysis["p_value"] = anomaly.get("p_value", 1.0)
    clusters = detect_clusters(records)
    analysis["n_clusters"] = clusters["n_clusters"]
    up = unified_probability(analysis)
    return generate_recommendations(up["risk_level"], up["unified_probability"], region=region)
