"""空間b値マッピング。グリッド上で局所b値を計算。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

def compute_spatial_bvalue(events: list[EarthquakeRecord], grid_spacing_deg: float = 0.5, radius_km: float = 100) -> dict:
    if len(events) < 20: return {"error": "最低20イベント必要"}
    lats = np.array([e.latitude for e in events]); lons = np.array([e.longitude for e in events]); mags = np.array([e.magnitude for e in events])
    lat_grid = np.arange(lats.min(), lats.max(), grid_spacing_deg); lon_grid = np.arange(lons.min(), lons.max(), grid_spacing_deg)
    grid = []
    for lat in lat_grid:
        for lon in lon_grid:
            dists = np.sqrt(((lats-lat)*_KM_PER_DEG)**2 + ((lons-lon)*_KM_PER_DEG*math.cos(math.radians(lat)))**2)
            mask = dists < radius_km
            local_mags = mags[mask]
            if len(local_mags) < 10: continue
            mc = np.percentile(local_mags, 30)
            above = local_mags[local_mags >= mc]
            if len(above) < 5: continue
            b = math.log10(math.e) / (np.mean(above) - (mc - 0.05))
            b = max(0.3, min(3.0, b))
            grid.append({"lat": round(float(lat),2), "lon": round(float(lon),2), "b_value": round(b,3), "n_events": int(len(above)), "mc": round(float(mc),1)})
    return {"grid": grid, "n_cells": len(grid), "n_events_total": len(events)}
