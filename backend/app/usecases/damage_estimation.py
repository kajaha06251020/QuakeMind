"""リアルタイム被害推定。震度分布 + 人口データで概算。"""
import math
import logging

logger = logging.getLogger(__name__)

# 主要都市の人口（概算、万人）
_CITY_POPULATIONS = [
    (43.06, 141.35, "札幌", 197),
    (38.27, 140.87, "仙台", 109),
    (35.68, 139.76, "東京", 1404),
    (35.45, 139.64, "横浜", 377),
    (35.10, 136.91, "名古屋", 233),
    (34.69, 135.50, "大阪", 275),
    (34.39, 132.46, "広島", 120),
    (33.59, 130.40, "福岡", 163),
]

_KM_PER_DEG = 111.0


def _intensity_at_city(magnitude: float, depth_km: float, distance_km: float) -> float:
    hypo_dist = math.sqrt(distance_km ** 2 + depth_km ** 2)
    hypo_dist = max(hypo_dist, 1.0)
    intensity = 2.68 + 1.0 * magnitude - 1.58 * math.log10(hypo_dist)
    return max(0.0, min(7.0, round(intensity, 2)))


def estimate_damage(
    source_lat: float, source_lon: float, source_depth_km: float, source_magnitude: float,
) -> dict:
    affected_cities = []
    total_affected_population = 0

    for city_lat, city_lon, city_name, pop_万 in _CITY_POPULATIONS:
        dlat = (city_lat - source_lat) * _KM_PER_DEG
        dlon = (city_lon - source_lon) * _KM_PER_DEG * math.cos(math.radians(source_lat))
        dist_km = math.sqrt(dlat ** 2 + dlon ** 2)
        intensity = _intensity_at_city(source_magnitude, source_depth_km, dist_km)

        if intensity >= 3.0:
            affected_pop = pop_万 * 10000
            total_affected_population += affected_pop
            affected_cities.append({
                "city": city_name,
                "distance_km": round(dist_km, 1),
                "estimated_intensity": intensity,
                "population": affected_pop,
            })

    affected_cities.sort(key=lambda x: x["estimated_intensity"], reverse=True)

    # 被害レベル判定
    max_intensity = max((c["estimated_intensity"] for c in affected_cities), default=0)
    if max_intensity >= 6.0:
        damage_level = "catastrophic"
    elif max_intensity >= 5.0:
        damage_level = "severe"
    elif max_intensity >= 4.0:
        damage_level = "moderate"
    elif max_intensity >= 3.0:
        damage_level = "minor"
    else:
        damage_level = "negligible"

    return {
        "source": {"latitude": source_lat, "longitude": source_lon, "depth_km": source_depth_km, "magnitude": source_magnitude},
        "damage_level": damage_level,
        "total_affected_population": total_affected_population,
        "affected_cities": affected_cities,
    }
