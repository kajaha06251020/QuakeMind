"""応力降下量推定。Bruneモデルでスペクトルから推定。"""
import math, logging
logger = logging.getLogger(__name__)

def estimate_stress_drop(magnitude: float, rupture_area_km2: float | None = None) -> dict:
    moment = 10**(1.5*magnitude+9.05)
    if rupture_area_km2 is None:
        rupture_area_km2 = 10**(-3.49+0.91*magnitude)
    area_m2 = rupture_area_km2 * 1e6
    radius_m = math.sqrt(area_m2/math.pi)
    # Eshelby (1957): Δσ = (7/16) * M0 / r^3
    stress_drop_pa = (7/16) * moment / max(radius_m**3, 1)
    stress_drop_mpa = stress_drop_pa / 1e6
    stress_drop_bar = stress_drop_mpa * 10
    # 典型値との比較
    if stress_drop_bar < 1: category = "very_low"
    elif stress_drop_bar < 10: category = "low"
    elif stress_drop_bar < 100: category = "normal"
    elif stress_drop_bar < 500: category = "high"
    else: category = "very_high"
    return {"magnitude": magnitude, "seismic_moment_nm": moment, "rupture_area_km2": round(rupture_area_km2,2), "equivalent_radius_km": round(radius_m/1000,2), "stress_drop_mpa": round(stress_drop_mpa,4), "stress_drop_bar": round(stress_drop_bar,2), "category": category}
