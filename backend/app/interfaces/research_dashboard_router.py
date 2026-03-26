"""研究ダッシュボード API ルーター。"""
from typing import Optional
from fastapi import APIRouter, Query
from app.services.research_journal import get_entries
from app.services.hypothesis_engine import get_active_hypotheses
from app.services.experiment_logger import get_experiment_logs
from app.services.pattern_memory import get_all_patterns
from app.services.research_scheduler import hourly_analysis, daily_analysis, weekly_analysis
from app.services.research_workflow import investigate_anomaly, investigate_large_earthquake
from app.services.model_evaluator import evaluate_etas_accuracy, evaluate_ml_accuracy

router = APIRouter(prefix="/research-dashboard", tags=["research-dashboard"])


@router.get("/overview")
async def dashboard_overview():
    """研究ダッシュボード概要。"""
    journal_entries, journal_total = await get_entries(limit=5)
    hypotheses = await get_active_hypotheses()
    experiments = await get_experiment_logs(limit=5)
    patterns = get_all_patterns()

    return {
        "journal": {"total": journal_total, "latest": journal_entries},
        "active_hypotheses": {"total": len(hypotheses), "list": hypotheses},
        "recent_experiments": experiments,
        "stored_patterns": len(patterns),
    }


@router.get("/journal")
async def get_journal(
    entry_type: Optional[str] = None, region: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
):
    entries, total = await get_entries(entry_type=entry_type, region=region, limit=limit, offset=offset)
    return {"entries": entries, "total": total}


@router.get("/hypotheses")
async def get_hypotheses():
    return {"hypotheses": await get_active_hypotheses()}


@router.get("/experiments")
async def get_experiments(name: Optional[str] = None, limit: int = Query(default=50)):
    return {"experiments": await get_experiment_logs(name=name, limit=limit)}


@router.post("/run/hourly")
async def run_hourly():
    return await hourly_analysis()


@router.post("/run/daily")
async def run_daily():
    return await daily_analysis()


@router.post("/run/weekly")
async def run_weekly():
    return await weekly_analysis()


@router.post("/investigate/anomaly")
async def run_investigate_anomaly(region: Optional[str] = None):
    return await investigate_anomaly(region)


@router.post("/investigate/earthquake")
async def run_investigate_earthquake(event_id: str = Query(...)):
    return await investigate_large_earthquake(event_id)
