"""イベント間時間の統計分析。ポアソン以外のモデルフィッティング。"""
import logging
import numpy as np
from scipy import stats
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)

def analyze_interevent_times(events: list[EarthquakeRecord]) -> dict:
    if len(events) < 20: return {"error": "最低20イベント必要"}
    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z","+00:00")).timestamp()
        except: return 0
    times = sorted([_ts(e) for e in events])
    intervals = np.diff(times)/3600  # hours
    intervals = intervals[intervals > 0]
    if len(intervals) < 10: return {"error": "有効な間隔が不足"}
    results = {"n_intervals": len(intervals), "mean_hours": round(float(np.mean(intervals)),2), "median_hours": round(float(np.median(intervals)),2), "cv": round(float(np.std(intervals)/np.mean(intervals)),3), "models": {}}
    # Exponential (Poisson)
    loc, scale = stats.expon.fit(intervals, floc=0)
    results["models"]["exponential"] = {"scale": round(scale,2), "ks_statistic": round(float(stats.kstest(intervals, "expon", args=(0,scale)).statistic),4)}
    # Gamma
    a, loc, scale = stats.gamma.fit(intervals, floc=0)
    results["models"]["gamma"] = {"shape": round(a,3), "scale": round(scale,2), "ks_statistic": round(float(stats.kstest(intervals, "gamma", args=(a,0,scale)).statistic),4)}
    # Weibull
    c, loc, scale = stats.weibull_min.fit(intervals, floc=0)
    results["models"]["weibull"] = {"shape": round(c,3), "scale": round(scale,2), "ks_statistic": round(float(stats.kstest(intervals, "weibull_min", args=(c,0,scale)).statistic),4)}
    best = min(results["models"].items(), key=lambda x: x[1]["ks_statistic"])
    results["best_model"] = best[0]
    results["poisson_departure"] = "significant" if results["cv"] > 1.3 or results["cv"] < 0.7 else "not_significant"
    return results
