"""Coulomb Rate-State (CRS) モデル。Dieterich (1994)。

クーロン応力変化を地震発生率の変化に変換する物理モデル。
ΔCFS → ΔR/R = exp(ΔCFS / (a * sigma))
"""
import math
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Rate-State パラメータ（日本標準）
_A_SIGMA = 0.01  # a * σ (MPa) — Dieterich 1994 標準値
_TA = 50.0  # 特性緩和時間（年）


def coulomb_to_rate_change(delta_cfs_mpa: float, a_sigma: float = _A_SIGMA) -> float:
    """クーロン応力変化から発生率変化率を計算する。

    R'/R = exp(ΔCFS / (a*σ))

    Args:
        delta_cfs_mpa: クーロン応力変化 (MPa)
        a_sigma: rate-state パラメータ a*σ (MPa)

    Returns:
        発生率変化率 (1.0 = 変化なし, >1 = 促進, <1 = 抑制)
    """
    return math.exp(delta_cfs_mpa / a_sigma)


def rate_state_forecast(
    background_rate: float,
    delta_cfs_mpa: float,
    forecast_days: float = 30.0,
    a_sigma: float = _A_SIGMA,
    ta_years: float = _TA,
) -> dict:
    """Rate-State モデルで応力変化後の発生率時系列を予測する。

    Dieterich (1994): R(t) = R0 / [1 + (exp(-ΔCFS/(a*σ)) - 1) * exp(-t/ta)]
    """
    ta_days = ta_years * 365.25
    rate_factor = coulomb_to_rate_change(delta_cfs_mpa, a_sigma)

    # 時系列計算
    times = np.linspace(0, forecast_days, 50)
    rates = []
    for t in times:
        denominator = 1 + (1 / rate_factor - 1) * math.exp(-t / ta_days)
        if denominator > 0:
            r = background_rate / denominator
        else:
            r = background_rate * rate_factor
        rates.append(r)

    # 累積予測イベント数（台形積分）
    cumulative = float(np.trapezoid(rates, times))

    # ピーク発生率
    peak_rate = max(rates)
    peak_time = float(times[rates.index(peak_rate)])

    return {
        "background_rate_per_day": round(background_rate, 4),
        "delta_cfs_mpa": round(delta_cfs_mpa, 6),
        "rate_change_factor": round(rate_factor, 4),
        "forecast_days": forecast_days,
        "cumulative_expected_events": round(cumulative, 2),
        "peak_rate_per_day": round(peak_rate, 4),
        "peak_time_days": round(peak_time, 1),
        "time_to_background_days": round(ta_days * 0.1, 1),  # ~10% 緩和
        "timeseries": [
            {"day": round(float(t), 1), "rate_per_day": round(float(r), 4)}
            for t, r in zip(times[::5], rates[::5])  # 10点に間引き
        ],
    }
