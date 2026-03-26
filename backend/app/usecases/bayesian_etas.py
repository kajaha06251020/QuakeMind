"""ベイズ ETAS — MCMC でパラメータ事後分布を推定し不確実性を定量化。"""
import math
import logging
from datetime import datetime, timezone

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)
_MC = 2.0


def _parse_ts(e: EarthquakeRecord) -> float:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _etas_log_likelihood(params, times_days, mags, T):
    mu, K, alpha, c, p = params
    if mu <= 0 or K <= 0 or alpha <= 0 or c <= 0 or p <= 0.5:
        return -1e10

    n = len(times_days)
    ll = 0.0

    for i in range(n):
        rate = mu
        for j in range(i):
            dt = times_days[i] - times_days[j]
            if dt > 0:
                rate += K * math.exp(alpha * (mags[j] - _MC)) / (dt + c) ** p
        if rate > 0:
            ll += math.log(rate)
        else:
            ll -= 10

    integral = mu * T
    for j in range(n):
        remaining = T - times_days[j]
        if remaining > 0 and p != 1:
            contrib = K * math.exp(alpha * (mags[j] - _MC))
            contrib *= (1 / (1 - p)) * ((remaining + c) ** (1 - p) - c ** (1 - p))
            integral += abs(contrib)
    ll -= integral
    return ll


def _log_prior(params):
    mu, K, alpha, c, p = params
    if mu <= 0 or K <= 0 or alpha <= 0 or c <= 0 or p <= 0.5:
        return -1e10
    # 弱情報事前分布 (log-normal)
    lp = 0.0
    lp -= 0.5 * (math.log(mu) - math.log(0.5)) ** 2
    lp -= 0.5 * (math.log(K) - math.log(0.05)) ** 2
    lp -= 0.5 * (math.log(alpha) - math.log(1.0)) ** 2
    lp -= 0.5 * (math.log(c) - math.log(0.01)) ** 2
    lp -= 0.5 * (math.log(p) - math.log(1.1)) ** 2 / 0.25
    return lp


def bayesian_etas_forecast(
    events: list[EarthquakeRecord],
    forecast_hours: int = 72,
    n_samples: int = 500,
    burn_in: int = 100,
) -> dict:
    """ベイズ ETAS: MCMC で事後分布を推定し、不確実性付き予測を返す。"""
    if len(events) < 15:
        return {"error": "最低15イベント必要", "n_events": len(events)}

    times_raw = np.array([_parse_ts(e) for e in events])
    mags = np.array([e.magnitude for e in events])
    order = np.argsort(times_raw)
    times_raw = times_raw[order]
    mags = mags[order]
    times_days = (times_raw - times_raw[0]) / 86400.0
    T = times_days[-1]

    if T <= 0:
        return {"error": "観測期間が0"}

    # Metropolis-Hastings MCMC
    current = np.array([0.5, 0.05, 1.0, 0.01, 1.1])
    current_ll = _etas_log_likelihood(current, times_days, mags, T) + _log_prior(current)
    proposal_std = np.array([0.1, 0.01, 0.2, 0.005, 0.1])

    samples = []
    accepted = 0
    rng = np.random.default_rng(42)

    for i in range(n_samples + burn_in):
        proposal = current + rng.normal(0, proposal_std)
        proposal = np.abs(proposal)  # 正値制約
        proposal[4] = max(proposal[4], 0.51)  # p > 0.5

        prop_ll = _etas_log_likelihood(proposal, times_days, mags, T) + _log_prior(proposal)
        log_ratio = prop_ll - current_ll

        if math.log(rng.uniform()) < log_ratio:
            current = proposal
            current_ll = prop_ll
            accepted += 1

        if i >= burn_in:
            samples.append(current.copy())

    samples = np.array(samples)
    acceptance_rate = accepted / (n_samples + burn_in)

    # 事後分布の要約統計量
    param_names = ["mu", "K", "alpha", "c", "p"]
    posterior = {}
    for idx, name in enumerate(param_names):
        vals = samples[:, idx]
        posterior[name] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "ci_2_5": round(float(np.percentile(vals, 2.5)), 4),
            "ci_97_5": round(float(np.percentile(vals, 97.5)), 4),
        }

    # 予測: 各サンプルで予測発生数を計算し、分布を返す
    forecast_days = forecast_hours / 24.0
    predicted_counts = []
    for s in samples[::max(1, len(samples) // 100)]:  # 最大100サンプル
        mu_s = s[0]
        expected = mu_s * forecast_days
        for j in range(len(times_days)):
            elapsed = T - times_days[j]
            if elapsed >= 0 and s[4] != 1:
                K_s, alpha_s, c_s, p_s = s[1], s[2], s[3], s[4]
                trig = K_s * math.exp(alpha_s * (mags[j] - _MC))
                trig *= (1 / (1 - p_s)) * ((elapsed + forecast_days + c_s) ** (1 - p_s) - (elapsed + c_s) ** (1 - p_s))
                expected += abs(trig)
        predicted_counts.append(expected)

    predicted_counts = np.array(predicted_counts)

    return {
        "forecast_hours": forecast_hours,
        "expected_events": {
            "mean": round(float(np.mean(predicted_counts)), 2),
            "std": round(float(np.std(predicted_counts)), 2),
            "ci_2_5": round(float(np.percentile(predicted_counts, 2.5)), 2),
            "ci_97_5": round(float(np.percentile(predicted_counts, 97.5)), 2),
        },
        "posterior_parameters": posterior,
        "acceptance_rate": round(acceptance_rate, 4),
        "n_samples": len(samples),
        "n_events": len(events),
        "observation_days": round(T, 1),
    }
