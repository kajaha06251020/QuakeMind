"""流体圧力-地震相関モデル。降雨/潮汐/ダム水位と地震発生率の因果分析。"""
import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


def correlate_fluid_signals(
    earthquake_counts: np.ndarray,
    precipitation_mm: np.ndarray | None = None,
    tidal_force: np.ndarray | None = None,
    reservoir_level_m: np.ndarray | None = None,
) -> dict:
    """外部環境要因と地震発生率の相関を分析する。"""
    n = len(earthquake_counts)
    results = {"n_days": n, "correlations": {}}

    signals = {}
    if precipitation_mm is not None and len(precipitation_mm) == n:
        signals["precipitation"] = precipitation_mm
    if tidal_force is not None and len(tidal_force) == n:
        signals["tidal_force"] = tidal_force
    if reservoir_level_m is not None and len(reservoir_level_m) == n:
        signals["reservoir_level"] = reservoir_level_m

    for name, signal in signals.items():
        # 同時相関
        r, p = stats.pearsonr(earthquake_counts, signal) if len(signal) >= 3 else (0, 1)

        # ラグ相関（1-7日のラグ）
        best_lag = 0
        best_lag_r = abs(r)
        for lag in range(1, min(8, n // 3)):
            if n - lag >= 3:
                r_lag, _ = stats.pearsonr(earthquake_counts[lag:], signal[:n-lag])
                if abs(r_lag) > best_lag_r:
                    best_lag_r = abs(r_lag)
                    best_lag = lag

        results["correlations"][name] = {
            "simultaneous_r": round(float(r), 4),
            "simultaneous_p": round(float(p), 6),
            "significant": p < 0.05,
            "best_lag_days": best_lag,
            "best_lag_r": round(float(best_lag_r), 4),
            "interpretation": (
                f"{name}と地震発生率に有意な相関（r={r:.3f}, p={p:.4f}）。ラグ{best_lag}日で最大相関{best_lag_r:.3f}。"
                if p < 0.05 else
                f"{name}と地震発生率に有意な相関は検出されなかった。"
            ),
        }

    if not signals:
        results["note"] = "外部環境データが提供されていません。降雨量、潮汐、ダム水位データを入力してください。"

    return results
