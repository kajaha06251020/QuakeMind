"""津波到達時間推定。浅水波速度 v = sqrt(g*h) で近似。"""
import math
import logging

logger = logging.getLogger(__name__)

_G = 9.81  # 重力加速度 m/s^2
_KM_PER_DEG = 111.0

# 日本の主要沿岸都市（緯度, 経度, 名前, 近海の平均水深m）
_COASTAL_CITIES = [
    (43.06, 141.35, "札幌", 200),
    (39.72, 140.10, "秋田", 300),
    (38.27, 140.87, "仙台", 200),
    (35.68, 139.76, "東京", 50),
    (35.10, 136.91, "名古屋", 30),
    (34.69, 135.50, "大阪", 30),
    (33.59, 130.40, "福岡", 50),
    (31.60, 130.56, "鹿児島", 200),
    (26.33, 127.80, "那覇", 500),
]


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def estimate_tsunami_arrival(
    source_lat: float, source_lon: float, source_depth_km: float, source_magnitude: float,
) -> dict:
    if source_magnitude < 6.5 or source_depth_km > 60:
        return {"tsunami_risk": False, "message": "津波リスクは低い（M<6.5 or 深度>60km）", "arrivals": []}

    arrivals = []
    for city_lat, city_lon, city_name, avg_depth_m in _COASTAL_CITIES:
        dist_km = _haversine_km(source_lat, source_lon, city_lat, city_lon)
        wave_speed_ms = math.sqrt(_G * avg_depth_m)
        wave_speed_kmh = wave_speed_ms * 3.6
        if wave_speed_kmh > 0:
            arrival_minutes = (dist_km / wave_speed_kmh) * 60
        else:
            arrival_minutes = 9999
        arrivals.append({"city": city_name, "distance_km": round(dist_km, 1), "arrival_minutes": round(arrival_minutes, 1), "wave_speed_kmh": round(wave_speed_kmh, 1)})

    arrivals.sort(key=lambda x: x["arrival_minutes"])
    return {"tsunami_risk": True, "source": {"latitude": source_lat, "longitude": source_lon, "depth_km": source_depth_km, "magnitude": source_magnitude}, "arrivals": arrivals}
