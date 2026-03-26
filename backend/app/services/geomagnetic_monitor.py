"""地磁気観測モニタリング。

気象庁の地磁気観測データを参照する。
異常検知フレームワーク + Kp指数の参照URL。
"""
import logging
import math

logger = logging.getLogger(__name__)

# NOAA SWPC Kp指数 参照URL
_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"

# 気象庁地磁気観測所
_OBSERVATORIES = [
    {"id": "KAK", "name": "柿岡", "lat": 36.23, "lon": 140.19},
    {"id": "MMB", "name": "女満別", "lat": 43.91, "lon": 144.19},
    {"id": "KNY", "name": "鹿屋", "lat": 31.42, "lon": 130.88},
    {"id": "CBI", "name": "父島", "lat": 27.10, "lon": 142.18},
]


def get_geomagnetic_info() -> dict:
    """地磁気観測情報と参照URLを返す。"""
    return {
        "kp_index_url": _KP_URL,
        "description": "地磁気異常は大地震の前兆として研究されているが、確実な予知手段ではない。Kp指数は太陽活動由来の磁気嵐指標。",
        "observatories": _OBSERVATORIES,
        "n_observatories": len(_OBSERVATORIES),
    }


def analyze_geomagnetic(
    observations: list[dict],  # [{"timestamp": str, "h_nt": float, "d_nt": float, "z_nt": float}]
    baseline_h: float = 30000.0,  # 日本の水平成分の通常値 (nT)
) -> dict:
    """地磁気データから異常を検出する。"""
    if not observations:
        return {"anomaly_detected": False, "message": "データなし"}

    h_values = [o.get("h_nt", baseline_h) for o in observations]
    deviations = [abs(h - baseline_h) for h in h_values]
    max_dev = max(deviations) if deviations else 0
    avg_dev = sum(deviations) / len(deviations) if deviations else 0

    # 異常判定: 100nT 以上の偏差
    anomaly = max_dev > 100.0

    return {
        "n_observations": len(observations),
        "baseline_h_nt": baseline_h,
        "avg_deviation_nt": round(avg_dev, 2),
        "max_deviation_nt": round(max_dev, 2),
        "anomaly_detected": anomaly,
        "threshold_nt": 100.0,
    }
