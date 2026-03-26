"""地震テクトニクスの自動分類。沈み込み帯/内陸直下型/海溝型を自動分類。"""
import logging

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 日本周辺のテクトニクス境界（簡易）
_TRENCH_ZONES = [
    {"name": "日本海溝", "lat_range": (35, 42), "lon_range": (141, 146), "max_depth": 600},
    {"name": "南海トラフ", "lat_range": (31, 35), "lon_range": (132, 140), "max_depth": 300},
    {"name": "相模トラフ", "lat_range": (34, 36), "lon_range": (139, 142), "max_depth": 200},
    {"name": "琉球海溝", "lat_range": (24, 31), "lon_range": (125, 132), "max_depth": 400},
]


def classify_tectonic_type(event: EarthquakeRecord) -> dict:
    """地震のテクトニクスタイプを自動分類する。"""
    lat, lon, depth = event.latitude, event.longitude, event.depth_km

    # 深発地震（最優先: どのゾーンにあっても深度 > 300 km は深発）
    if depth > 300:
        return {
            "type": "deep_focus",
            "subtype": "deep_mantle",
            "zone": "深発地震帯",
            "confidence": 0.8,
            "description": f"深発地震（深度{depth}km）。沈み込むプレート内部での発生。",
        }

    # 海溝型判定
    for zone in _TRENCH_ZONES:
        lat_min, lat_max = zone["lat_range"]
        lon_min, lon_max = zone["lon_range"]
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            if depth > 30:
                return {
                    "type": "subduction_interface",
                    "subtype": "interplate" if depth < 60 else "intraslab",
                    "zone": zone["name"],
                    "confidence": 0.8 if depth < zone["max_depth"] else 0.5,
                    "description": f"{zone['name']}付近のプレート境界型地震（深度{depth}km）",
                }

    # 内陸直下型
    if depth < 30:
        # 日本列島内（陸域）の浅い地震
        if 30 <= lat <= 46 and 128 <= lon <= 146:
            return {
                "type": "crustal",
                "subtype": "shallow_inland",
                "zone": "日本列島内陸",
                "confidence": 0.7,
                "description": f"内陸直下型地震（深度{depth}km）。活断層による可能性。",
            }

    # デフォルト
    return {
        "type": "unclassified",
        "subtype": "unknown",
        "zone": "分類不能",
        "confidence": 0.3,
        "description": "分類基準に合致しない地震。追加情報が必要。",
    }


def classify_events(events: list[EarthquakeRecord]) -> dict:
    """複数イベントのテクトニクス分類統計を返す。"""
    if not events:
        return {"total": 0, "classifications": {}}

    counts: dict[str, int] = {}
    for e in events:
        result = classify_tectonic_type(e)
        t = result["type"]
        counts[t] = counts.get(t, 0) + 1

    return {
        "total": len(events),
        "classifications": counts,
        "dominant_type": max(counts, key=counts.get) if counts else None,
    }
