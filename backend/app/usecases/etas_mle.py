"""ETAS パラメータ最尤推定。

蓄積データから地域ごとの最適 ETAS パラメータを推定する。
Ogata (1988) の対数尤度関数を scipy.optimize.minimize で最大化。
"""
import math
import logging
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_MC = 2.0  # カタログ完全性マグニチュード


def _parse_ts(e: EarthquakeRecord) -> float:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _log_likelihood(params: np.ndarray, times: np.ndarray, mags: np.ndarray, T: float) -> float:
    """ETAS 対数尤度関数（負値、最小化用）。"""
    mu, K, alpha, c, p = params

    if mu <= 0 or K <= 0 or alpha <= 0 or c <= 0 or p <= 0:
        return 1e10

    n = len(times)
    ll = 0.0

    for i in range(n):
        # λ(ti) = μ + Σ_{j<i} K * exp(α(Mj - Mc)) / (ti - tj + c)^p
        rate = mu
        for j in range(i):
            dt = (times[i] - times[j]) / 86400.0  # 秒→日
            if dt > 0:
                rate += K * math.exp(alpha * (mags[j] - _MC)) / (dt + c) ** p

        if rate > 0:
            ll += math.log(rate)
        else:
            ll -= 10  # ペナルティ

    # 積分項: ∫_0^T λ(t) dt ≈ μT + Σ K*exp(α(Mi-Mc)) * ∫ (t+c)^(-p) dt
    integral = mu * T
    for j in range(n):
        remaining = (T - (times[j] - times[0]) / 86400.0)
        if remaining > 0 and p != 1:
            contrib = K * math.exp(alpha * (mags[j] - _MC))
            contrib *= (1 / (1 - p)) * ((remaining + c) ** (1 - p) - c ** (1 - p))
            integral += contrib

    ll -= integral
    return -ll  # 最小化するので負


def estimate_etas_parameters(
    events: list[EarthquakeRecord],
    initial_params: dict | None = None,
) -> dict:
    """ETAS パラメータを最尤推定する。

    Returns:
        {"mu", "K", "alpha", "c", "p", "log_likelihood", "n_events", "converged"}
    """
    if len(events) < 20:
        return {"error": "パラメータ推定には最低20イベント必要", "n_events": len(events)}

    times = np.array([_parse_ts(e) for e in events])
    mags = np.array([e.magnitude for e in events])

    # 時間でソート
    order = np.argsort(times)
    times = times[order]
    mags = mags[order]

    T = (times[-1] - times[0]) / 86400.0  # 観測期間（日）
    if T <= 0:
        return {"error": "観測期間が0", "n_events": len(events)}

    # 初期値
    defaults = {"mu": 0.5, "K": 0.05, "alpha": 1.0, "c": 0.01, "p": 1.1}
    if initial_params:
        defaults.update(initial_params)

    x0 = np.array([defaults["mu"], defaults["K"], defaults["alpha"], defaults["c"], defaults["p"]])

    # 制約: 全パラメータ > 0
    bounds = [(0.001, 10), (0.001, 1), (0.1, 5), (0.001, 1), (0.5, 2.5)]

    try:
        result = minimize(
            _log_likelihood, x0, args=(times, mags, T),
            method="L-BFGS-B", bounds=bounds,
            options={"maxiter": 100, "ftol": 1e-6},
        )

        mu, K, alpha, c, p = result.x
        return {
            "mu": round(float(mu), 4),
            "K": round(float(K), 4),
            "alpha": round(float(alpha), 4),
            "c": round(float(c), 4),
            "p": round(float(p), 4),
            "log_likelihood": round(float(-result.fun), 2),
            "n_events": len(events),
            "converged": bool(result.success),
            "observation_days": round(T, 1),
        }
    except Exception as e:
        logger.error("[ETAS-MLE] 推定エラー: %s", e)
        return {"error": str(e), "n_events": len(events)}
