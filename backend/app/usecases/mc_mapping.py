"""Mc空間マッピング。カタログ完全性の空間分布を可視化。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

def compute_mc_map(events: list[EarthquakeRecord], grid_spacing_deg: float = 0.5, radius_km: float = 100) -> dict:
    if len(events) < 20: return {"error": "最低20イベント必要"}
    lats = np.array([e.latitude for e in events]); lons = np.array([e.longitude for e in events]); mags = np.array([e.magnitude for e in events])
    grid = []
    for lat in np.arange(lats.min(), lats.max(), grid_spacing_deg):
        for lon in np.arange(lons.min(), lons.max(), grid_spacing_deg):
            dists = np.sqrt(((lats-lat)*_KM_PER_DEG)**2+((lons-lon)*_KM_PER_DEG*math.cos(math.radians(lat)))**2)
            local = mags[dists < radius_km]
            if len(local) < 10: continue
            bins = np.arange(local.min(), local.max()+0.1, 0.1)
            counts = np.array([np.sum(local>=b) for b in bins])
            mc = float(bins[np.argmax(counts)]) if len(counts)>0 else float(local.min())
            grid.append({"lat": round(float(lat),2), "lon": round(float(lon),2), "mc": round(mc,1), "n_events": int(len(local))})
    return {"grid": grid, "n_cells": len(grid), "mean_mc": round(float(np.mean([g["mc"] for g in grid])),2) if grid else 0}
