"""類似地震検索。マグニチュード・深度・地域で類似イベントを検索。"""
import math
import logging

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def find_similar_events(
    target: EarthquakeRecord,
    catalog: list[EarthquakeRecord],
    max_results: int = 5,
    mag_tolerance: float = 0.5,
    depth_tolerance_km: float = 20.0,
    distance_tolerance_km: float = 100.0,
) -> list[dict]:
    """targetに類似したイベントをcatalogから検索する。"""

    def _haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return 2 * R * math.asin(min(1.0, math.sqrt(a)))

    def _similarity(e: EarthquakeRecord) -> float:
        if e.event_id == target.event_id:
            return -1  # 自分自身は除外
        mag_diff = abs(e.magnitude - target.magnitude)
        depth_diff = abs(e.depth_km - target.depth_km)
        dist_km = _haversine(target.latitude, target.longitude, e.latitude, e.longitude)

        mag_score = max(0, 1 - mag_diff / mag_tolerance)
        depth_score = max(0, 1 - depth_diff / depth_tolerance_km)
        dist_score = max(0, 1 - dist_km / distance_tolerance_km)

        return mag_score * 0.4 + depth_score * 0.2 + dist_score * 0.4

    scored = [(e, _similarity(e)) for e in catalog]
    scored = [(e, s) for e, s in scored if s > 0.1]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            "event_id": e.event_id,
            "magnitude": e.magnitude,
            "depth_km": e.depth_km,
            "latitude": e.latitude,
            "longitude": e.longitude,
            "timestamp": e.timestamp,
            "similarity_score": round(s, 4),
        }
        for e, s in scored[:max_results]
    ]
