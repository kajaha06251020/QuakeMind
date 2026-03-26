"""CSEP方式のモデル比較。対数尤度比で予測モデルを公平に評価。"""
import math, logging
import numpy as np
logger = logging.getLogger(__name__)

def csep_comparison(predictions: list[dict]) -> dict:
    """複数モデルの予測を CSEP N-test, L-test で評価する。
    predictions: [{"model": str, "predicted_rate": float, "observed_count": int}, ...]
    """
    if not predictions: return {"error": "予測データなし"}
    results = []
    for p in predictions:
        model = p["model"]; rate = max(p["predicted_rate"], 0.01); observed = p["observed_count"]
        # N-test: 予測数 vs 観測数の比較
        n_ratio = observed / rate if rate > 0 else 0
        # L-test: ポアソン対数尤度
        log_L = observed * math.log(rate) - rate - sum(math.log(k+1) for k in range(observed))
        # Information gain per earthquake
        ig = (log_L - (observed * math.log(max(observed,0.01)/1) - observed)) / max(observed, 1) if observed > 0 else 0
        results.append({"model": model, "predicted_rate": rate, "observed_count": observed, "n_ratio": round(n_ratio,3), "log_likelihood": round(log_L,2), "information_gain": round(ig,4)})
    results.sort(key=lambda r: r["log_likelihood"], reverse=True)
    return {"rankings": results, "best_model": results[0]["model"] if results else None, "n_models": len(results)}
