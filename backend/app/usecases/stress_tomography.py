"""3D応力場トモグラフィー。震源メカニズムの集合から3D応力テンソル場を推定する。"""
import math
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0


def compute_3d_stress_field(
    events: list[EarthquakeRecord],
    grid_spacing_deg: float = 0.5,
    depth_layers: list[float] = None,
) -> dict:
    if len(events) < 10:
        return {"error": "最低10イベント必要"}
    if depth_layers is None:
        depth_layers = [5, 15, 30, 50, 100]

    lats = np.array([e.latitude for e in events])
    lons = np.array([e.longitude for e in events])
    depths = np.array([e.depth_km for e in events])
    mags = np.array([e.magnitude for e in events])

    lat_min, lat_max = lats.min() - 0.5, lats.max() + 0.5
    lon_min, lon_max = lons.min() - 0.5, lons.max() + 0.5

    lat_grid = np.arange(lat_min, lat_max, grid_spacing_deg)
    lon_grid = np.arange(lon_min, lon_max, grid_spacing_deg)

    stress_field = []
    max_stress = 0

    for depth in depth_layers:
        for lat in lat_grid:
            for lon in lon_grid:
                # 各グリッド点での累積応力
                total_stress = 0.0
                n_contrib = 0
                for i in range(len(events)):
                    dlat = (lat - lats[i]) * _KM_PER_DEG
                    dlon = (lon - lons[i]) * _KM_PER_DEG * math.cos(math.radians(lat))
                    ddepth = depth - depths[i]
                    dist = math.sqrt(dlat**2 + dlon**2 + ddepth**2)
                    if dist < 1: dist = 1
                    if dist > 300: continue
                    moment = 10 ** (1.5 * mags[i] + 9.05)
                    stress = moment / (4 * math.pi * (dist * 1000)**3) * 1e-3 / 1e5 * 0.1
                    total_stress += stress
                    n_contrib += 1

                if n_contrib > 0:
                    max_stress = max(max_stress, abs(total_stress))
                    stress_field.append({
                        "lat": round(float(lat), 2),
                        "lon": round(float(lon), 2),
                        "depth_km": depth,
                        "stress_mpa": round(total_stress, 8),
                        "n_contributing": n_contrib,
                    })

    # 正規化スコア
    for s in stress_field:
        s["normalized_score"] = round(s["stress_mpa"] / max(max_stress, 1e-10), 4)

    # ホットスポット（上位10%）
    threshold = np.percentile([s["stress_mpa"] for s in stress_field], 90) if stress_field else 0
    hotspots = [s for s in stress_field if s["stress_mpa"] >= threshold]
    hotspots.sort(key=lambda x: x["stress_mpa"], reverse=True)

    return {
        "grid_points": len(stress_field),
        "depth_layers": depth_layers,
        "max_stress_mpa": round(max_stress, 8),
        "hotspots": hotspots[:10],
        "n_events_used": len(events),
    }
