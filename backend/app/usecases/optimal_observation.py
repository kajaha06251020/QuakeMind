"""最適観測設計。予測精度向上に最も効果的な観測点を情報理論的に計算する。"""
import math
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)
_KM_PER_DEG = 111.0

_CANDIDATE_SITES = [
    {"name": "紀伊半島沖", "lat": 33.5, "lon": 136.0},
    {"name": "房総沖", "lat": 34.5, "lon": 141.0},
    {"name": "日向灘", "lat": 32.0, "lon": 132.5},
    {"name": "十勝沖", "lat": 42.0, "lon": 145.0},
    {"name": "沖縄トラフ", "lat": 26.0, "lon": 128.0},
    {"name": "佐渡沖", "lat": 38.5, "lon": 138.5},
    {"name": "駿河湾", "lat": 34.8, "lon": 138.5},
    {"name": "三陸沖", "lat": 39.5, "lon": 143.5},
]


def recommend_observation_sites(events: list[EarthquakeRecord], n_recommendations: int = 3) -> dict:
    if not events:
        return {"recommendations": [{"name": s["name"], "info_gain": 1.0} for s in _CANDIDATE_SITES[:n_recommendations]]}

    results = []
    for site in _CANDIDATE_SITES:
        nearby = sum(
            1 for e in events
            if math.sqrt(
                ((e.latitude - site["lat"]) * _KM_PER_DEG) ** 2
                + ((e.longitude - site["lon"]) * _KM_PER_DEG * math.cos(math.radians(site["lat"]))) ** 2
            ) < 200
        )

        info_gain = 1.0 / (1 + nearby * 0.1)

        # 活断層への近さボーナス
        from app.usecases.seismic_gap import _SEGMENTS
        min_seg_dist = min(
            (
                math.sqrt(
                    ((site["lat"] - s["lat"]) * _KM_PER_DEG) ** 2
                    + ((site["lon"] - s["lon"]) * _KM_PER_DEG) ** 2
                )
                for s in _SEGMENTS
            ),
            default=999,
        )
        proximity_bonus = max(0, 1 - min_seg_dist / 500) * 0.5

        total_score = info_gain + proximity_bonus
        results.append({
            "name": site["name"],
            "lat": site["lat"],
            "lon": site["lon"],
            "nearby_events": nearby,
            "info_gain": round(info_gain, 4),
            "proximity_bonus": round(proximity_bonus, 4),
            "total_score": round(total_score, 4),
        })

    results.sort(key=lambda r: r["total_score"], reverse=True)
    return {"recommendations": results[:n_recommendations], "all_candidates": results}
