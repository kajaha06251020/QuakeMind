"""能動学習。予測精度向上に最も寄与するデータを特定する。"""
import logging
import math
import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 日本の地域グリッド
_REGIONS = [
    {"name": "北海道", "lat": 43.0, "lon": 143.0},
    {"name": "東北", "lat": 39.0, "lon": 140.0},
    {"name": "関東", "lat": 36.0, "lon": 140.0},
    {"name": "中部", "lat": 36.0, "lon": 137.0},
    {"name": "近畿", "lat": 35.0, "lon": 135.5},
    {"name": "中国", "lat": 35.0, "lon": 133.0},
    {"name": "四国", "lat": 33.5, "lon": 133.5},
    {"name": "九州", "lat": 33.0, "lon": 131.0},
    {"name": "沖縄", "lat": 26.5, "lon": 128.0},
]

_KM_PER_DEG = 111.0


def identify_data_gaps(events: list[EarthquakeRecord]) -> dict:
    """データギャップを特定する。どの地域のデータが不足しているか。"""
    region_counts = {r["name"]: 0 for r in _REGIONS}

    for e in events:
        min_dist = float("inf")
        nearest = None
        for r in _REGIONS:
            dist = math.sqrt((e.latitude - r["lat"]) ** 2 + (e.longitude - r["lon"]) ** 2) * _KM_PER_DEG
            if dist < min_dist:
                min_dist = dist
                nearest = r["name"]
        if nearest:
            region_counts[nearest] += 1

    total = max(sum(region_counts.values()), 1)

    gaps = []
    for name, count in sorted(region_counts.items(), key=lambda x: x[1]):
        density = count / total
        info_gain = -math.log2(density + 0.01)  # 情報利得（低密度ほど高い）
        gaps.append({
            "region": name,
            "event_count": count,
            "density_ratio": round(density, 4),
            "information_gain": round(info_gain, 3),
            "priority": "high" if density < 0.05 else "medium" if density < 0.1 else "low",
        })

    # 最も情報利得が高い地域
    gaps.sort(key=lambda x: x["information_gain"], reverse=True)

    return {
        "n_events_total": len(events),
        "data_gaps": gaps,
        "recommendations": [
            f"{g['region']}: データ増強推奨（現在{g['event_count']}件、情報利得{g['information_gain']:.2f}）"
            for g in gaps if g["priority"] == "high"
        ],
    }


def compute_model_uncertainty_map(events: list[EarthquakeRecord]) -> list[dict]:
    """各地域での予測不確実性を推定する。不確実性が高い地域 = データが必要。"""
    uncertainty_map = []

    for r in _REGIONS:
        # この地域のイベント数
        nearby = [e for e in events if math.sqrt((e.latitude - r["lat"]) ** 2 + (e.longitude - r["lon"]) ** 2) * _KM_PER_DEG < 300]
        n = len(nearby)

        # 不確実性 ∝ 1/sqrt(n)
        uncertainty = 1.0 / math.sqrt(max(n, 1))

        # マグニチュード範囲のカバレッジ
        if nearby:
            mag_std = float(np.std([e.magnitude for e in nearby])) if len(nearby) > 1 else 0
            coverage = min(1.0, mag_std / 2.0)  # std=2がフルカバレッジ
        else:
            coverage = 0.0

        uncertainty_map.append({
            "region": r["name"],
            "latitude": r["lat"],
            "longitude": r["lon"],
            "n_nearby_events": n,
            "prediction_uncertainty": round(uncertainty, 4),
            "magnitude_coverage": round(coverage, 4),
            "data_need_score": round(uncertainty * (1 - coverage), 4),
        })

    uncertainty_map.sort(key=lambda x: x["data_need_score"], reverse=True)
    return uncertainty_map
