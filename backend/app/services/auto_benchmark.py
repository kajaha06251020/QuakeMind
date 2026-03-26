"""自動ベンチマーク。CSEP基準でQuakeMindの予測精度を毎週自動評価。"""
import logging, math
import numpy as np
logger = logging.getLogger(__name__)

def run_benchmark(predictions: list[dict], observations: list[dict]) -> dict:
    """予測と観測を比較してスコアリングする。
    predictions: [{"bin": str, "rate": float}]
    observations: [{"bin": str, "count": int}]
    """
    if not predictions or not observations: return {"error": "データなし"}
    pred_map = {p["bin"]: p["rate"] for p in predictions}
    obs_map = {o["bin"]: o["count"] for o in observations}
    all_bins = set(pred_map.keys()) | set(obs_map.keys())
    # N-test
    total_pred = sum(pred_map.values()); total_obs = sum(obs_map.values())
    n_test = {"predicted_total": round(total_pred,1), "observed_total": total_obs, "ratio": round(total_obs/max(total_pred,0.01),3)}
    # L-test (log-likelihood)
    ll = 0
    for b in all_bins:
        rate = max(pred_map.get(b, 0.01), 0.01); obs = obs_map.get(b, 0)
        ll += obs * math.log(rate) - rate
    # Information gain
    uniform_rate = max(total_obs / max(len(all_bins), 1), 0.01)
    ll_uniform = sum(obs_map.get(b,0)*math.log(uniform_rate)-uniform_rate for b in all_bins)
    ig = (ll - ll_uniform) / max(total_obs, 1)
    return {"n_test": n_test, "log_likelihood": round(ll,2), "information_gain_per_eq": round(ig,4), "n_bins": len(all_bins), "grade": "A" if ig > 0.5 else "B" if ig > 0 else "C" if ig > -0.5 else "F"}
