"""マルチハザード・カスケードシミュレーター。地震→津波→火災→停電→交通遮断の連鎖。"""
import math, logging

logger = logging.getLogger(__name__)


def simulate_cascade(
    magnitude: float, depth_km: float, latitude: float, longitude: float,
    population_density: float = 5000,  # 人/km²
) -> dict:
    """カスケード災害をシミュレーションする。"""

    # Phase 1: 地震
    intensity = 2.68 + 1.0 * magnitude - 1.58 * math.log10(max(math.sqrt(100**2 + depth_km**2), 1))
    intensity = max(0, min(7, intensity))

    cascade = {"phases": [], "total_affected_population": 0, "total_economic_loss_billion_yen": 0}

    # Phase 1: 揺れ被害
    building_damage_rate = min(0.5, max(0, (intensity - 4) * 0.1))
    affected_area_km2 = math.pi * (magnitude * 15) ** 2
    affected_pop = int(affected_area_km2 * population_density * building_damage_rate)
    economic_loss = affected_pop * 0.001  # 10億円単位の概算

    cascade["phases"].append({
        "phase": 1, "hazard": "earthquake_shaking",
        "intensity": round(intensity, 1),
        "building_damage_rate": round(building_damage_rate, 3),
        "affected_population": affected_pop,
        "economic_loss_billion_yen": round(economic_loss, 1),
    })
    cascade["total_affected_population"] += affected_pop
    cascade["total_economic_loss_billion_yen"] += economic_loss

    # Phase 2: 津波（M6.5以上 + 浅い + 海域）
    if magnitude >= 6.5 and depth_km < 60:
        wave_height_m = 10 ** (0.5 * magnitude - 3.3)
        coastal_affected = int(wave_height_m * 1000 * 50)  # 概算
        tsunami_loss = coastal_affected * 0.005
        cascade["phases"].append({
            "phase": 2, "hazard": "tsunami",
            "estimated_wave_height_m": round(wave_height_m, 1),
            "coastal_affected": coastal_affected,
            "economic_loss_billion_yen": round(tsunami_loss, 1),
        })
        cascade["total_affected_population"] += coastal_affected
        cascade["total_economic_loss_billion_yen"] += tsunami_loss

    # Phase 3: 火災（震度6以上）
    if intensity >= 5.5:
        fire_probability = min(0.8, (intensity - 5) * 0.2)
        fire_affected = int(affected_pop * fire_probability * 0.3)
        fire_loss = fire_affected * 0.002
        cascade["phases"].append({
            "phase": 3, "hazard": "fire",
            "fire_probability": round(fire_probability, 3),
            "fire_affected": fire_affected,
            "economic_loss_billion_yen": round(fire_loss, 1),
        })
        cascade["total_affected_population"] += fire_affected
        cascade["total_economic_loss_billion_yen"] += fire_loss

    # Phase 4: 停電
    if intensity >= 4.5:
        blackout_rate = min(0.9, (intensity - 4) * 0.2)
        blackout_pop = int(affected_area_km2 * population_density * blackout_rate)
        cascade["phases"].append({
            "phase": 4, "hazard": "power_outage",
            "blackout_rate": round(blackout_rate, 3),
            "affected_population": blackout_pop,
            "estimated_recovery_hours": int(24 * (intensity - 3)),
        })

    # Phase 5: 交通遮断
    if intensity >= 4.0:
        road_closure_rate = min(0.8, (intensity - 3.5) * 0.15)
        cascade["phases"].append({
            "phase": 5, "hazard": "transportation_disruption",
            "road_closure_rate": round(road_closure_rate, 3),
            "rail_suspended": intensity >= 4.5,
            "estimated_recovery_days": max(1, int((intensity - 3) * 2)),
        })

    cascade["n_phases"] = len(cascade["phases"])
    cascade["cascade_severity"] = "catastrophic" if cascade["total_economic_loss_billion_yen"] > 100 else "severe" if cascade["total_economic_loss_billion_yen"] > 10 else "moderate" if cascade["total_economic_loss_billion_yen"] > 1 else "minor"

    return cascade
