"""地震モーメントレート追跡。エネルギー放出速度の時系列。"""
import math, logging
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)

def compute_moment_rate(events: list[EarthquakeRecord], bin_days: int = 7) -> dict:
    if len(events) < 5: return {"error": "イベント数不足"}
    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z","+00:00"))
        except: return datetime(2000,1,1,tzinfo=timezone.utc)
    sorted_e = sorted(events, key=_ts); timestamps = [_ts(e) for e in sorted_e]
    first = timestamps[0].date(); last = timestamps[-1].date()
    n_days = (last-first).days+1
    bins = defaultdict(float)
    for e, t in zip(sorted_e, timestamps):
        bin_idx = (t.date()-first).days // bin_days
        moment = 10**(1.5*e.magnitude+9.05)
        bins[bin_idx] += moment
    timeseries = [{"bin": i, "start": (first+timedelta(days=i*bin_days)).isoformat(), "moment_nm": bins.get(i,0), "log10_moment": round(math.log10(max(bins.get(i,0),1)),2)} for i in range(n_days//bin_days+1)]
    moments = [b["moment_nm"] for b in timeseries]
    return {"timeseries": timeseries, "total_moment": sum(moments), "max_moment": max(moments) if moments else 0, "n_bins": len(timeseries), "equivalent_single_magnitude": round((math.log10(max(sum(moments),1))-9.05)/1.5,1)}
