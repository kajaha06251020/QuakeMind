"""事前計算シナリオDB。主要断層のシナリオを事前計算して格納する。"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_scenario_cache: dict[str, dict] = {}


def precompute_scenarios() -> dict:
    """主要シナリオを事前計算する。"""
    from app.usecases.scenario_engine import PRESET_SCENARIOS, simulate_scenario

    computed = 0
    for key, s in PRESET_SCENARIOS.items():
        if key not in _scenario_cache:
            _scenario_cache[key] = simulate_scenario(s["lat"], s["lon"], s["mag"], s["depth"], s["name"])
            _scenario_cache[key]["precomputed_at"] = datetime.now(timezone.utc).isoformat()
            computed += 1

    return {"computed": computed, "total_cached": len(_scenario_cache), "scenario_keys": list(_scenario_cache.keys())}


def get_cached_scenario(key: str) -> dict | None:
    return _scenario_cache.get(key)


def find_nearest_scenario(lat: float, lon: float, magnitude: float) -> dict | None:
    """最も近い事前計算済みシナリオを返す。"""
    import math
    if not _scenario_cache:
        precompute_scenarios()

    best = None
    best_dist = float("inf")

    for key, scenario in _scenario_cache.items():
        src = scenario.get("source", {})
        dlat = (lat - src.get("latitude", 0)) * 111
        dlon = (lon - src.get("longitude", 0)) * 111
        dmag = abs(magnitude - src.get("magnitude", 0)) * 50
        dist = math.sqrt(dlat**2 + dlon**2 + dmag**2)
        if dist < best_dist:
            best_dist = dist
            best = {"scenario_key": key, "distance_score": round(dist, 1), **scenario}

    return best
