"""クーロン応力変化（ΔCFS）の簡易計算。

点震源近似。Okada (1992) の完全実装ではなく、
距離減衰に基づく経験的な応力変化推定。
"""
import math
import logging

logger = logging.getLogger(__name__)

_MU_FRICTION = 0.4  # 見かけの摩擦係数


def _moment_from_magnitude(magnitude: float) -> float:
    """マグニチュードからモーメント (N*m) を計算。"""
    return 10 ** (1.5 * magnitude + 9.05)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def _stress_change_at_point(
    moment: float, distance_km: float, depth_km: float,
) -> float:
    """点震源からの距離における応力変化 (bar)。

    簡易モデル: ΔCFS ∝ M0 / r^3
    """
    r = math.sqrt(distance_km ** 2 + depth_km ** 2)
    r_m = max(r * 1000.0, 1000.0)  # メートル変換、最小1km
    # 応力 (Pa) = M0 / (4π * r^3) * 定数
    stress_pa = moment / (4 * math.pi * r_m ** 3) * 1e-3
    stress_bar = stress_pa / 1e5  # Pa → bar
    return stress_bar


def compute_coulomb_stress(
    source_lat: float,
    source_lon: float,
    source_depth_km: float,
    source_magnitude: float,
    grid_spacing_deg: float = 0.5,
    grid_radius_deg: float = 2.0,
) -> dict:
    """
    震源周辺のグリッド上でクーロン応力変化を計算する。

    Returns:
        {"source_event": {...}, "stress_changes": [{"lat", "lon", "distance_km", "delta_cfs_bar"}, ...]}
    """
    moment = _moment_from_magnitude(source_magnitude)

    import numpy as np
    lats = np.arange(
        source_lat - grid_radius_deg,
        source_lat + grid_radius_deg + grid_spacing_deg / 2,
        grid_spacing_deg,
    )
    lons = np.arange(
        source_lon - grid_radius_deg,
        source_lon + grid_radius_deg + grid_spacing_deg / 2,
        grid_spacing_deg,
    )

    stress_changes = []
    for lat in lats:
        for lon in lons:
            dist = _haversine_km(source_lat, source_lon, float(lat), float(lon))
            if dist < 1.0:  # 震源直上は除外
                continue
            delta_cfs = _stress_change_at_point(moment, dist, source_depth_km)
            stress_changes.append({
                "lat": round(float(lat), 2),
                "lon": round(float(lon), 2),
                "distance_km": round(dist, 1),
                "delta_cfs_bar": round(delta_cfs, 6),
            })

    return {
        "source_event": {
            "latitude": source_lat,
            "longitude": source_lon,
            "depth_km": source_depth_km,
            "magnitude": source_magnitude,
            "moment_nm": moment,
        },
        "stress_changes": stress_changes,
    }
