"""地震ダブレット検出。短時間で連発する同規模の地震ペア。"""
import math, logging
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

def detect_doublets(events: list[EarthquakeRecord], time_threshold_hours: float = 24, dist_threshold_km: float = 50, mag_threshold: float = 0.5) -> dict:
    if len(events) < 5: return {"doublets": [], "n_doublets": 0}
    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z","+00:00")).timestamp()
        except: return 0
    sorted_e = sorted(events, key=_ts); doublets = []
    for i in range(len(sorted_e)-1):
        for j in range(i+1, min(i+20, len(sorted_e))):
            dt_hours = (_ts(sorted_e[j])-_ts(sorted_e[i]))/3600
            if dt_hours > time_threshold_hours: break
            dist = math.sqrt(((sorted_e[i].latitude-sorted_e[j].latitude)*_KM_PER_DEG)**2+((sorted_e[i].longitude-sorted_e[j].longitude)*_KM_PER_DEG)**2)
            if dist < dist_threshold_km and abs(sorted_e[i].magnitude-sorted_e[j].magnitude) < mag_threshold:
                doublets.append({"event_a": sorted_e[i].event_id, "event_b": sorted_e[j].event_id, "time_gap_hours": round(dt_hours,1), "distance_km": round(dist,1), "mag_a": sorted_e[i].magnitude, "mag_b": sorted_e[j].magnitude})
    return {"n_doublets": len(doublets), "doublets": doublets[:30]}
