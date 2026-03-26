"""複数GMPE並行評価。3つの距離減衰式を比較。"""
import math, logging
import numpy as np
logger = logging.getLogger(__name__)

def _si_midorikawa(M, R): return max(0, min(7, 2.68 + 1.0*M - 1.58*math.log10(max(R,1))))
def _zhao2006(M, R): return max(0, min(7, 2.5 + 1.1*M - 1.7*math.log10(max(R,1)) - 0.003*R))
def _morikawa2013(M, R): return max(0, min(7, 2.7 + 0.95*M - 1.5*math.log10(max(R,1)) - 0.002*R))

def evaluate_multi_gmpe(magnitude: float, distance_km: float, depth_km: float = 10) -> dict:
    R = math.sqrt(distance_km**2 + depth_km**2)
    results = {
        "si_midorikawa_1999": round(_si_midorikawa(magnitude, R), 2),
        "zhao_2006": round(_zhao2006(magnitude, R), 2),
        "morikawa_fujiwara_2013": round(_morikawa2013(magnitude, R), 2),
    }
    vals = list(results.values())
    results["mean"] = round(float(np.mean(vals)), 2)
    results["epistemic_uncertainty"] = round(float(np.std(vals)), 3)
    results["range"] = round(max(vals) - min(vals), 2)
    return {"magnitude": magnitude, "distance_km": distance_km, "depth_km": depth_km, "gmpe_results": results}
