"""ShakeMap — 揺れ推定グリッド。Si & Midorikawa (1999) 距離減衰式。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0


def _intensity_at_point(magnitude: float, depth_km: float, distance_km: float) -> float:
    """推定震度 (JMA scale)。"""
    hypo_dist = math.sqrt(distance_km ** 2 + depth_km ** 2)
    hypo_dist = max(hypo_dist, 1.0)
    intensity = 2.68 + 1.0 * magnitude - 1.58 * math.log10(hypo_dist)
    return max(0.0, min(7.0, round(intensity, 2)))


def compute_shakemap(
    source_lat: float, source_lon: float, source_depth_km: float, source_magnitude: float,
    grid_spacing_deg: float = 0.2, grid_radius_deg: float = 3.0,
) -> dict:
    lats = np.arange(source_lat - grid_radius_deg, source_lat + grid_radius_deg + grid_spacing_deg / 2, grid_spacing_deg)
    lons = np.arange(source_lon - grid_radius_deg, source_lon + grid_radius_deg + grid_spacing_deg / 2, grid_spacing_deg)

    grid = []
    for lat in lats:
        for lon in lons:
            dlat = (float(lat) - source_lat) * _KM_PER_DEG
            dlon = (float(lon) - source_lon) * _KM_PER_DEG * math.cos(math.radians(source_lat))
            dist_km = math.sqrt(dlat ** 2 + dlon ** 2)
            intensity = _intensity_at_point(source_magnitude, source_depth_km, dist_km)
            if intensity >= 0.5:
                grid.append({"lat": round(float(lat), 3), "lon": round(float(lon), 3), "intensity": intensity, "distance_km": round(dist_km, 1)})

    return {"source": {"latitude": source_lat, "longitude": source_lon, "depth_km": source_depth_km, "magnitude": source_magnitude}, "grid": grid, "resolution_deg": grid_spacing_deg}
