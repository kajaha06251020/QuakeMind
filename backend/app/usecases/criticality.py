"""非平衡統計力学。地殻の臨界状態への近さを定量化する。"""
import math
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def compute_criticality_index(events: list[EarthquakeRecord]) -> dict:
    """臨界状態指標を計算する。

    指標:
    1. b値偏差（b=1.0が臨界状態）
    2. 相関長（空間的クラスタリングの範囲）
    3. 揺らぎの増大（発生率の分散/平均比）
    """
    if len(events) < 20:
        return {"error": "最低20イベント必要"}

    mags = np.array([e.magnitude for e in events])

    # 1. b値偏差: |b - 1.0|が小さいほど臨界的
    mc = np.percentile(mags, 30)
    above_mc = mags[mags >= mc]
    if len(above_mc) >= 5:
        b = math.log10(math.e) / (np.mean(above_mc) - (mc - 0.05))
        b = max(0.3, min(3.0, b))
        b_deviation = abs(b - 1.0)
    else:
        b = 1.0
        b_deviation = 0

    # 2. 空間相関長（平均イベント間距離）
    lats = np.array([e.latitude for e in events])
    lons = np.array([e.longitude for e in events])
    if len(events) > 1:
        dists = []
        n = min(len(events), 100)
        for i in range(n):
            for j in range(i+1, min(i+10, n)):
                d = math.sqrt(((lats[i]-lats[j])*111)**2 + ((lons[i]-lons[j])*111*math.cos(math.radians(lats[i])))**2)
                dists.append(d)
        correlation_length = float(np.mean(dists)) if dists else 0
    else:
        correlation_length = 0

    # 3. 揺らぎ: 発生率のFano factor (variance/mean)
    from datetime import datetime as dt, timezone as tz
    def _ts(e):
        try: return dt.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except: return dt(2000, 1, 1, tzinfo=tz.utc)

    timestamps = sorted([_ts(e) for e in events])
    if len(timestamps) >= 10:
        from collections import Counter
        daily = Counter(t.date() for t in timestamps)
        first = timestamps[0].date()
        last = timestamps[-1].date()
        n_days = (last - first).days + 1
        from datetime import timedelta
        counts = [daily.get(first + timedelta(days=d), 0) for d in range(n_days)]
        mean_rate = np.mean(counts) if counts else 1
        var_rate = np.var(counts) if counts else 0
        fano_factor = var_rate / max(mean_rate, 0.01)
    else:
        fano_factor = 1.0

    # 臨界指標（0-1、1が最も臨界的）
    b_score = max(0, 1 - b_deviation * 2)
    fano_score = min(1, fano_factor / 3)
    corr_score = min(1, correlation_length / 200)

    criticality_index = (b_score * 0.4 + fano_score * 0.3 + corr_score * 0.3)

    if criticality_index >= 0.7:
        state = "near_critical"
        description = "臨界状態に近い。大地震発生の可能性が高まっている"
    elif criticality_index >= 0.4:
        state = "approaching_critical"
        description = "臨界状態に近づいている。注意深い監視が必要"
    else:
        state = "subcritical"
        description = "臨界状態から離れている。通常の背景活動"

    return {
        "criticality_index": round(criticality_index, 4),
        "state": state,
        "description": description,
        "components": {
            "b_value": round(b, 3),
            "b_deviation": round(b_deviation, 3),
            "b_score": round(b_score, 4),
            "correlation_length_km": round(correlation_length, 1),
            "correlation_score": round(corr_score, 4),
            "fano_factor": round(fano_factor, 3),
            "fluctuation_score": round(fano_score, 4),
        },
        "n_events": len(events),
    }
