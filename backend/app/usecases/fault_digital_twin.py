"""日本列島断層デジタルツイン。全主要断層の応力状態をリアルタイム追跡。"""
import math
import logging
from datetime import datetime, timezone
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

_FAULTS = [
    {"id": "nankai", "name": "南海トラフ", "lat": 33.0, "lon": 135.0, "max_m": 9.0, "last_event_year": 1946, "recurrence_years": 150},
    {"id": "tokai", "name": "東海", "lat": 34.5, "lon": 138.0, "max_m": 8.5, "last_event_year": 1854, "recurrence_years": 150},
    {"id": "sagami", "name": "相模トラフ", "lat": 35.0, "lon": 139.5, "max_m": 8.0, "last_event_year": 1923, "recurrence_years": 200},
    {"id": "itoigawa", "name": "糸魚川-静岡", "lat": 36.0, "lon": 138.0, "max_m": 7.5, "last_event_year": 1714, "recurrence_years": 1000},
    {"id": "tachikawa", "name": "立川断層帯", "lat": 35.7, "lon": 139.4, "max_m": 7.4, "last_event_year": -1000, "recurrence_years": 10000},
    {"id": "japan_trench", "name": "日本海溝", "lat": 38.5, "lon": 143.0, "max_m": 9.0, "last_event_year": 2011, "recurrence_years": 600},
]


def compute_digital_twin(events: list[EarthquakeRecord], current_year: int = 2026) -> dict:
    twin = []
    for fault in _FAULTS:
        elapsed = current_year - fault["last_event_year"]
        loading_pct = min(100, elapsed / fault["recurrence_years"] * 100)

        # 周辺の地震活動
        nearby = [
            e for e in events
            if math.sqrt(
                ((e.latitude - fault["lat"]) * _KM_PER_DEG) ** 2
                + ((e.longitude - fault["lon"]) * _KM_PER_DEG * math.cos(math.radians(fault["lat"]))) ** 2
            ) < 200
        ]

        # 累積応力
        stress = 0.0
        for e in nearby:
            dist = math.sqrt(
                ((e.latitude - fault["lat"]) * _KM_PER_DEG) ** 2
                + ((e.longitude - fault["lon"]) * _KM_PER_DEG * math.cos(math.radians(fault["lat"]))) ** 2
            )
            if dist < 1:
                dist = 1
            moment = 10 ** (1.5 * e.magnitude + 9.05)
            stress += moment / (4 * math.pi * (dist * 1000) ** 3) * 1e-3 / 1e5 * 0.1

        status = "critical" if loading_pct > 80 else "elevated" if loading_pct > 50 else "normal"

        twin.append({
            "fault_id": fault["id"],
            "name": fault["name"],
            "loading_percent": round(loading_pct, 1),
            "elapsed_years": elapsed,
            "recurrence_years": fault["recurrence_years"],
            "max_magnitude": fault["max_m"],
            "nearby_events": len(nearby),
            "cumulative_stress_mpa": round(stress, 8),
            "status": status,
        })

    twin.sort(key=lambda f: f["loading_percent"], reverse=True)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "faults": twin,
        "most_loaded": twin[0]["name"] if twin else None,
    }
