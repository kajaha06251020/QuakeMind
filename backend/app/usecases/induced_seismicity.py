"""誘発地震識別器。人間活動との時空間相関で誘発/自然を判定する。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 誘発地震源の典型パターン
_INJECTION_WELLS = [
    {"name": "北海道苫小牧CCS", "lat": 42.63, "lon": 141.73, "type": "CO2_injection"},
]
_DAMS = [
    {"name": "黒部ダム", "lat": 36.57, "lon": 137.66, "capacity_m3": 199e6},
    {"name": "奥只見ダム", "lat": 37.12, "lon": 139.20, "capacity_m3": 601e6},
]
_GEOTHERMAL = [
    {"name": "八丈島地熱", "lat": 33.11, "lon": 139.80},
    {"name": "松川地熱", "lat": 39.85, "lon": 140.73},
]

_KM_PER_DEG = 111.0


def classify_induced(events: list[EarthquakeRecord], custom_sources: list[dict] | None = None) -> dict:
    """地震イベントが誘発か自然かを判定する。"""
    sources = []
    for w in _INJECTION_WELLS: sources.append({**w, "category": "injection"})
    for d in _DAMS: sources.append({**d, "category": "dam"})
    for g in _GEOTHERMAL: sources.append({**g, "category": "geothermal"})
    if custom_sources: sources.extend(custom_sources)

    results = []
    for e in events:
        min_dist = float("inf")
        nearest_source = None
        for s in sources:
            dlat = (e.latitude - s["lat"]) * _KM_PER_DEG
            dlon = (e.longitude - s["lon"]) * _KM_PER_DEG * math.cos(math.radians(e.latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist < min_dist:
                min_dist = dist
                nearest_source = s

        # 判定基準: 10km以内 + M<5 = 誘発の可能性高
        if min_dist < 10 and e.magnitude < 5:
            classification = "likely_induced"
            confidence = min(0.9, 1 - min_dist / 10)
        elif min_dist < 30 and e.magnitude < 4:
            classification = "possibly_induced"
            confidence = 0.3 + (30 - min_dist) / 60
        else:
            classification = "natural"
            confidence = min(0.95, min_dist / 50)

        results.append({
            "event_id": e.event_id, "magnitude": e.magnitude,
            "classification": classification, "confidence": round(confidence, 3),
            "nearest_source": nearest_source["name"] if nearest_source else None,
            "distance_km": round(min_dist, 1),
        })

    induced = sum(1 for r in results if r["classification"] != "natural")
    return {
        "total_events": len(events),
        "likely_induced": sum(1 for r in results if r["classification"] == "likely_induced"),
        "possibly_induced": sum(1 for r in results if r["classification"] == "possibly_induced"),
        "natural": sum(1 for r in results if r["classification"] == "natural"),
        "events": results[:50],  # 最大50件
    }
