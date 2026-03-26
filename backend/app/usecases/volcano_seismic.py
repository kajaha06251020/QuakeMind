"""火山-地震相互作用分析。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

_VOLCANOES = [
    {"name": "富士山", "lat": 35.36, "lon": 138.73, "alert_level": 1},
    {"name": "桜島", "lat": 31.59, "lon": 130.66, "alert_level": 3},
    {"name": "阿蘇山", "lat": 32.88, "lon": 131.10, "alert_level": 2},
    {"name": "浅間山", "lat": 36.40, "lon": 138.52, "alert_level": 2},
    {"name": "箱根山", "lat": 35.23, "lon": 139.02, "alert_level": 1},
]

def analyze_volcano_seismic(events: list[EarthquakeRecord], radius_km: float = 30) -> dict:
    if not events: return {"volcanoes": [], "n_analyzed": 0}
    results = []
    for v in _VOLCANOES:
        nearby = [e for e in events if math.sqrt(((e.latitude-v["lat"])*_KM_PER_DEG)**2+((e.longitude-v["lon"])*_KM_PER_DEG*math.cos(math.radians(v["lat"])))**2) < radius_km]
        if nearby:
            mags = [e.magnitude for e in nearby]
            shallow = [e for e in nearby if e.depth_km < 10]
            results.append({"volcano": v["name"], "alert_level": v["alert_level"], "nearby_events": len(nearby), "max_magnitude": round(max(mags),1), "shallow_events": len(shallow), "volcanic_seismicity": len(shallow) > 5, "risk_note": f"火山性地震{len(shallow)}件検出" if len(shallow) > 5 else "通常"})
        else:
            results.append({"volcano": v["name"], "alert_level": v["alert_level"], "nearby_events": 0, "volcanic_seismicity": False})
    return {"volcanoes": results, "n_analyzed": len(results)}
