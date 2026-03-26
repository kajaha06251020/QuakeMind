"""シナリオシミュレーションエンジン。「もしM9が起きたら」の完全シナリオを自動生成。"""
import logging
from datetime import datetime, timezone

from app.usecases.shakemap import compute_shakemap
from app.usecases.tsunami_arrival import estimate_tsunami_arrival
from app.usecases.damage_estimation import estimate_damage
from app.usecases.etas import etas_forecast
from app.usecases.cascade import compute_cascade_probability
from app.usecases.finite_fault import estimate_fault_geometry
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def simulate_scenario(
    source_lat: float, source_lon: float, magnitude: float, depth_km: float = 15.0,
    scenario_name: str = "カスタムシナリオ",
) -> dict:
    """完全地震シナリオをシミュレーションする。"""

    # 1. 断層モデル
    fault = estimate_fault_geometry(magnitude, depth_km)

    # 2. 揺れ分布
    shake = compute_shakemap(source_lat, source_lon, depth_km, magnitude, grid_spacing_deg=0.5, grid_radius_deg=5.0)
    max_intensity = max((p["intensity"] for p in shake["grid"]), default=0)
    severe_area = sum(1 for p in shake["grid"] if p["intensity"] >= 5.0)

    # 3. 津波
    tsunami = estimate_tsunami_arrival(source_lat, source_lon, depth_km, magnitude)

    # 4. 被害推定
    damage = estimate_damage(source_lat, source_lon, depth_km, magnitude)

    # 5. 余震予測
    mock_event = EarthquakeRecord(
        event_id=f"scenario-{scenario_name}", magnitude=magnitude,
        latitude=source_lat, longitude=source_lon, depth_km=depth_km,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    aftershock = etas_forecast([mock_event], forecast_hours=72)

    # 6. カスケード
    cascade = compute_cascade_probability(source_lat, source_lon, magnitude)
    highest_cascade = cascade["fault_cascade"][0] if cascade["fault_cascade"] else None

    # 7. 総合影響評価
    if magnitude >= 8.0 and tsunami["tsunami_risk"]:
        impact_level = "catastrophic"
        summary = f"M{magnitude}の巨大地震。広範囲で震度6以上、津波リスクあり。{damage['total_affected_population']:,}人が影響。"
    elif magnitude >= 7.0:
        impact_level = "severe"
        summary = f"M{magnitude}の大地震。{damage['damage_level']}レベルの被害。72時間で{aftershock['expected_events']:.0f}件の余震予測。"
    elif magnitude >= 6.0:
        impact_level = "significant"
        summary = f"M{magnitude}の地震。局所的に強い揺れ。被害は{damage['damage_level']}レベル。"
    else:
        impact_level = "moderate"
        summary = f"M{magnitude}の地震。被害は限定的。"

    return {
        "scenario_name": scenario_name,
        "source": {"latitude": source_lat, "longitude": source_lon, "magnitude": magnitude, "depth_km": depth_km},
        "impact_level": impact_level,
        "summary": summary,
        "fault_model": {"rupture_length_km": fault["rupture_length_km"], "rupture_area_km2": fault["rupture_area_km2"], "average_slip_m": fault["average_slip_m"]},
        "shaking": {"max_intensity": max_intensity, "severe_area_grid_points": severe_area},
        "tsunami": {"risk": tsunami["tsunami_risk"], "earliest_arrival_min": tsunami["arrivals"][0]["arrival_minutes"] if tsunami.get("arrivals") else None},
        "damage": {"level": damage["damage_level"], "affected_population": damage["total_affected_population"], "affected_cities": len(damage["affected_cities"])},
        "aftershocks": {"expected_72h": aftershock["expected_events"], "probability_m4_plus": aftershock["probability_m4_plus"]},
        "cascade": {"highest_risk_fault": highest_cascade["fault_name"] if highest_cascade else None, "probability": highest_cascade["cascade_probability_7day"] if highest_cascade else 0},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# 事前定義シナリオ
PRESET_SCENARIOS = {
    "nankai_m9": {"name": "南海トラフ巨大地震", "lat": 33.0, "lon": 135.0, "mag": 9.0, "depth": 15},
    "nankai_m8": {"name": "南海トラフM8", "lat": 33.0, "lon": 135.0, "mag": 8.0, "depth": 20},
    "tokai_m8": {"name": "東海地震", "lat": 34.5, "lon": 138.0, "mag": 8.5, "depth": 15},
    "capital_m7": {"name": "首都直下地震", "lat": 35.68, "lon": 139.76, "mag": 7.3, "depth": 10},
    "tohoku_m9": {"name": "東北沖（2011型）", "lat": 38.3, "lon": 142.4, "mag": 9.0, "depth": 24},
}


def run_preset_scenario(scenario_key: str) -> dict:
    if scenario_key not in PRESET_SCENARIOS:
        return {"error": f"不明なシナリオ: {scenario_key}", "available": list(PRESET_SCENARIOS.keys())}
    s = PRESET_SCENARIOS[scenario_key]
    return simulate_scenario(s["lat"], s["lon"], s["mag"], s["depth"], s["name"])
