"""地震カスケード確率。断層ネットワーク上での応力伝播を計算する。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)

# 日本の主要活断層（簡易リスト）
_FAULT_NETWORK = [
    {"id": "nankai", "name": "南海トラフ", "lat": 33.0, "lon": 135.0, "max_m": 9.0, "length_km": 700},
    {"id": "tokai", "name": "東海", "lat": 34.5, "lon": 138.0, "max_m": 8.5, "length_km": 200},
    {"id": "suruga", "name": "駿河トラフ", "lat": 34.8, "lon": 138.5, "max_m": 8.0, "length_km": 150},
    {"id": "sagami", "name": "相模トラフ", "lat": 35.0, "lon": 139.5, "max_m": 8.0, "length_km": 200},
    {"id": "itoigawa", "name": "糸魚川-静岡構造線", "lat": 36.0, "lon": 138.0, "max_m": 7.5, "length_km": 250},
    {"id": "tachikawa", "name": "立川断層帯", "lat": 35.7, "lon": 139.4, "max_m": 7.4, "length_km": 33},
]

_KM_PER_DEG = 111.0


def compute_cascade_probability(
    source_lat: float, source_lon: float, source_magnitude: float,
) -> dict:
    """震源から各断層への応力伝播に基づくカスケード確率を計算する。"""

    # 震源からのモーメント
    moment = 10 ** (1.5 * source_magnitude + 9.05)

    results = []
    for fault in _FAULT_NETWORK:
        dlat = (fault["lat"] - source_lat) * _KM_PER_DEG
        dlon = (fault["lon"] - source_lon) * _KM_PER_DEG * math.cos(math.radians(source_lat))
        dist_km = math.sqrt(dlat ** 2 + dlon ** 2)

        if dist_km < 1:
            dist_km = 1

        # 応力変化（簡易点震源モデル）
        r_m = dist_km * 1000
        delta_cfs = moment / (4 * math.pi * r_m ** 3) * 1e-3 / 1e5  # bar
        delta_cfs_mpa = delta_cfs * 0.1  # bar → MPa

        # Rate-State 発生率変化
        a_sigma = 0.01  # MPa
        rate_change = math.exp(min(delta_cfs_mpa / a_sigma, 20))  # cap at exp(20)

        # 背景確率（30年確率からの日別変換）
        p30yr = 0.01  # デフォルト
        p_daily_bg = 1 - (1 - p30yr) ** (1 / (30 * 365.25))
        p_daily_enhanced = min(0.99, 1 - (1 - p_daily_bg) ** rate_change)

        # 7日間のカスケード確率
        p_7day = 1 - (1 - p_daily_enhanced) ** 7

        results.append({
            "fault_id": fault["id"],
            "fault_name": fault["name"],
            "distance_km": round(dist_km, 1),
            "delta_cfs_mpa": round(delta_cfs_mpa, 8),
            "rate_change_factor": round(min(rate_change, 1e6), 2),
            "cascade_probability_7day": round(p_7day, 6),
            "max_magnitude": fault["max_m"],
        })

    results.sort(key=lambda x: x["cascade_probability_7day"], reverse=True)

    return {
        "source": {"latitude": source_lat, "longitude": source_lon, "magnitude": source_magnitude},
        "fault_cascade": results,
        "highest_risk_fault": results[0]["fault_name"] if results else None,
    }
