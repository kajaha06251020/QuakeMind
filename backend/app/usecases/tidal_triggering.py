"""潮汐トリガリング分析。Schuster検定で潮汐-地震の位相相関を検定。"""
import math, logging
import numpy as np
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)

def schuster_test(events: list[EarthquakeRecord], period_hours: float = 12.42) -> dict:
    """Schuster (1897) 検定。地震発生時刻の潮汐位相が一様分布かを検定。"""
    if len(events) < 20: return {"error": "最低20イベント必要"}
    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z","+00:00")).timestamp()
        except: return 0
    times = np.array([_ts(e) for e in events])
    period_sec = period_hours * 3600
    phases = (times % period_sec) / period_sec * 2 * np.pi
    # Schuster統計量
    D2 = (np.sum(np.cos(phases)))**2 + (np.sum(np.sin(phases)))**2
    n = len(phases)
    p_value = math.exp(-D2/n) if n > 0 else 1.0
    mean_phase = math.atan2(np.sum(np.sin(phases)), np.sum(np.cos(phases)))
    mean_phase_hours = (mean_phase / (2*math.pi)) * period_hours
    return {"n_events": n, "period_hours": period_hours, "schuster_D2": round(float(D2),2), "p_value": round(float(p_value),6), "triggered": p_value < 0.05, "preferred_phase_hours": round(float(mean_phase_hours),2), "interpretation": f"潮汐トリガリング{'あり' if p_value<0.05 else 'なし'}（p={p_value:.4f}）"}
