"""クーロン応力履歴の累積追跡。全過去地震からの応力変化を累積する。"""
import math
import logging

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0


def _point_source_stress(moment, dist_km, depth_km):
    r_m = math.sqrt((dist_km * 1000) ** 2 + (depth_km * 1000) ** 2)
    r_m = max(r_m, 1000)
    return moment / (4 * math.pi * r_m ** 3) * 1e-3 / 1e5 * 0.1  # MPa


def compute_cumulative_stress(
    events: list[EarthquakeRecord],
    target_lat: float,
    target_lon: float,
    target_depth_km: float = 15.0,
) -> dict:
    """対象地点での累積クーロン応力変化を計算する。"""
    if not events:
        return {"cumulative_stress_mpa": 0, "n_contributing_events": 0, "history": []}

    cumulative = 0.0
    history = []

    sorted_events = sorted(events, key=lambda e: e.timestamp)

    for e in sorted_events:
        dlat = (target_lat - e.latitude) * _KM_PER_DEG
        dlon = (target_lon - e.longitude) * _KM_PER_DEG * math.cos(math.radians(target_lat))
        dist_km = math.sqrt(dlat ** 2 + dlon ** 2)

        if dist_km > 500:  # 500km以上は無視
            continue

        moment = 10 ** (1.5 * e.magnitude + 9.05)
        delta_cfs = _point_source_stress(moment, dist_km, e.depth_km)
        cumulative += delta_cfs

        history.append({
            "event_id": e.event_id,
            "magnitude": e.magnitude,
            "distance_km": round(dist_km, 1),
            "delta_cfs_mpa": round(delta_cfs, 8),
            "cumulative_mpa": round(cumulative, 6),
            "timestamp": e.timestamp,
        })

    # 応力状態の解釈
    if cumulative > 0.01:
        state = "stress_loading"
        interpretation = f"累積応力 {cumulative:.4f} MPa（地震促進）"
    elif cumulative < -0.01:
        state = "stress_shadow"
        interpretation = f"累積応力 {cumulative:.4f} MPa（応力影、地震抑制）"
    else:
        state = "neutral"
        interpretation = "累積応力変化は中立"

    return {
        "target": {"latitude": target_lat, "longitude": target_lon, "depth_km": target_depth_km},
        "cumulative_stress_mpa": round(cumulative, 6),
        "state": state,
        "interpretation": interpretation,
        "n_contributing_events": len(history),
        "history": history[-20:],  # 最新20件
    }
