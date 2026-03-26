"""連鎖確率マップ。

ETAS モデルの空間拡張版。各グリッドセルでの今後N時間以内の
地震発生確率を計算する。
"""
import math
import logging
from datetime import datetime, timedelta, timezone

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# ETAS パラメータ（etas.py と共通）
_K = 0.05
_ALPHA = 1.0
_C = 0.01
_P = 1.1
_MC = 2.0
_MU = 0.5  # 背景発生率 (件/日)

# 空間減衰パラメータ
_D = 20.0   # 空間スケール (km)
_Q = 1.5    # 空間減衰指数

_KM_PER_DEG = 111.0


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def _spatial_kernel(distance_km: float) -> float:
    """空間減衰カーネル。"""
    return _D ** (2 * _Q) / (distance_km ** 2 + _D ** 2) ** _Q


def _temporal_kernel(elapsed_days: float, magnitude: float) -> float:
    """時間トリガーカーネル。"""
    if elapsed_days < 0 or magnitude < _MC:
        return 0.0
    return _K * math.exp(_ALPHA * (magnitude - _MC)) / (elapsed_days + _C) ** _P


def compute_chain_probability(
    events: list[EarthquakeRecord],
    forecast_hours: int = 24,
    grid_spacing_deg: float = 0.5,
    grid_radius_deg: float = 2.0,
) -> dict:
    """
    各グリッドセルでの今後 forecast_hours 以内の地震発生確率を計算。

    Returns:
        {"grid": [{"lat", "lon", "probability", "expected_rate"}, ...], "resolution_deg": float, "forecast_hours": int}
    """
    if not events:
        return {"grid": [], "resolution_deg": grid_spacing_deg, "forecast_hours": forecast_hours}

    timestamps = [_parse_ts(e) for e in events]
    latest = max(timestamps)
    forecast_days = forecast_hours / 24.0

    # グリッド中心を計算
    center_lat = np.mean([e.latitude for e in events])
    center_lon = np.mean([e.longitude for e in events])

    lats = np.arange(center_lat - grid_radius_deg, center_lat + grid_radius_deg + grid_spacing_deg / 2, grid_spacing_deg)
    lons = np.arange(center_lon - grid_radius_deg, center_lon + grid_radius_deg + grid_spacing_deg / 2, grid_spacing_deg)

    grid = []
    for lat in lats:
        for lon in lons:
            total_rate = _MU * forecast_days / (len(lats) * len(lons))  # 背景を均等配分

            for event, ts in zip(events, timestamps):
                elapsed = (latest - ts).total_seconds() / 86400.0
                dlat = (float(lat) - event.latitude) * _KM_PER_DEG
                dlon = (float(lon) - event.longitude) * _KM_PER_DEG * math.cos(math.radians(event.latitude))
                dist_km = math.sqrt(dlat ** 2 + dlon ** 2)

                temporal = _temporal_kernel(elapsed, event.magnitude)
                spatial = _spatial_kernel(max(dist_km, 0.1))
                rate_contribution = temporal * spatial * forecast_days
                total_rate += rate_contribution

            # ポアソン確率: P(X>=1) = 1 - exp(-rate)
            probability = 1.0 - math.exp(-total_rate)

            grid.append({
                "lat": round(float(lat), 2),
                "lon": round(float(lon), 2),
                "probability": round(min(probability, 1.0), 6),
                "expected_rate": round(total_rate, 4),
            })

    return {"grid": grid, "resolution_deg": grid_spacing_deg, "forecast_hours": forecast_hours}
