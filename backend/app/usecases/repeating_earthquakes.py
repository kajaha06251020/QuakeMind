"""反復地震検出。同じ断層パッチで繰り返し発生する地震ペアを検出。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

def detect_repeaters(events: list[EarthquakeRecord], dist_threshold_km: float = 2.0, mag_threshold: float = 0.3) -> dict:
    if len(events) < 10: return {"error": "最低10イベント必要", "repeaters": []}
    repeaters = []
    for i in range(len(events)):
        for j in range(i+1, len(events)):
            ei, ej = events[i], events[j]
            dist = math.sqrt(((ei.latitude-ej.latitude)*_KM_PER_DEG)**2+((ei.longitude-ej.longitude)*_KM_PER_DEG*math.cos(math.radians(ei.latitude)))**2)
            mag_diff = abs(ei.magnitude-ej.magnitude)
            if dist < dist_threshold_km and mag_diff < mag_threshold:
                repeaters.append({"event_a": ei.event_id, "event_b": ej.event_id, "distance_km": round(dist,2), "mag_diff": round(mag_diff,2), "magnitude": round((ei.magnitude+ej.magnitude)/2,1)})
    return {"n_repeaters": len(repeaters), "repeaters": repeaters[:50], "n_events_analyzed": len(events)}
