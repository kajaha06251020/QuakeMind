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


@router.get("/uncertainty-decomposition")
async def uncertainty_decomp(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.uncertainty_decomposition import decompose_uncertainty
    records = await _get_records(region, start, end)
    return decompose_uncertainty(records)


@router.get("/generate-paper")
async def gen_paper(region: Optional[str] = None):
    from app.services.paper_generator import generate_paper
    from fastapi.responses import PlainTextResponse
    result = generate_paper(f"QuakeMind 研究報告: {region or '全域'}", {}, region)
    return PlainTextResponse(content=result["markdown"], media_type="text/markdown")


@router.get("/global-patterns")
async def global_patterns(
    b_value: float = Query(default=1.0),
    rate_change: float = Query(default=1.0),
    n_clusters: int = Query(default=0),
    max_magnitude: float = Query(default=4.0),
):
    from app.services.global_learning import search_global_patterns
    return search_global_patterns({"b_value": b_value, "rate_change_ratio": rate_change, "n_clusters": n_clusters, "max_magnitude": max_magnitude})


@router.post("/resolve-contradictions")
async def resolve_contradictions(predictions: dict):
    from app.services.contradiction_resolver import resolve_and_explain
    return resolve_and_explain(predictions)


@router.get("/adaptive-intervals")
async def adaptive_intervals(risk_level: str = Query(default="normal")):
    from app.services.adaptive_collection import compute_adaptive_intervals
    return compute_adaptive_intervals(risk_level)


@router.get("/scenario-db")
async def scenario_database():
    from app.services.scenario_db import precompute_scenarios
    return precompute_scenarios()


@router.get("/scenario-db/nearest")
async def nearest_scenario(
    lat: float = Query(...),
    lon: float = Query(...),
    magnitude: float = Query(...),
):
    from app.services.scenario_db import find_nearest_scenario
    return find_nearest_scenario(lat, lon, magnitude)


@router.get("/induced-seismicity")
async def induced(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.induced_seismicity import classify_induced
    records = await _get_records(region, start, end)
    return classify_induced(records)


@router.get("/fault-healing")
async def fault_healing(fault_name: Optional[str] = None):
    from app.usecases.fault_healing import estimate_healing_rate
    return estimate_healing_rate(fault_name)


@router.post("/climate-correlation")
async def climate_corr(data: dict):
    from app.usecases.climate_seismicity import analyze_climate_earthquake_correlation
    import numpy as np
    return analyze_climate_earthquake_correlation(
        np.array(data.get("earthquake_counts", [])),
        sea_level_mm=np.array(data["sea_level_mm"]) if "sea_level_mm" in data else None,
        temperature_anomaly_c=np.array(data["temperature_c"]) if "temperature_c" in data else None,
    )


@router.get("/multi-hazard-cascade")
async def cascade_sim(lat: float = Query(...), lon: float = Query(...), magnitude: float = Query(...), depth_km: float = Query(default=15)):
    from app.usecases.multi_hazard_cascade import simulate_cascade
    return simulate_cascade(magnitude, depth_km, lat, lon)


@router.get("/communicate-risk")
async def communicate(probability: float = Query(...), audience: str = Query(default="general"), timeframe: str = Query(default="7日間")):
    from app.services.uncertainty_communicator import communicate_risk
    return communicate_risk(probability, audience=audience, timeframe=timeframe)
