"""くりこみ群解析。地震のスケール不変性を定量化する。"""
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def renormalization_analysis(events: list[EarthquakeRecord]) -> dict:
    if len(events) < 20:
        return {"error": "最低20イベント必要"}

    mags = np.array([e.magnitude for e in events])

    # マグニチュード-頻度のべき乗則チェック
    unique_mags = np.sort(np.unique(np.round(mags, 1)))[::-1]
    cumulative = np.array([np.sum(mags >= m) for m in unique_mags], dtype=float)

    valid = cumulative > 0
    if np.sum(valid) < 3:
        return {"error": "有効なデータ点が不足"}

    log_n = np.log10(cumulative[valid])
    log_m = unique_mags[valid]

    coeffs = np.polyfit(log_m, log_n, 1)
    b_value = -coeffs[0]
    residuals = log_n - np.polyval(coeffs, log_m)
    r_squared = 1 - np.var(residuals) / np.var(log_n) if np.var(log_n) > 0 else 0

    # スケール不変性の度合い（R²が1に近いほどべき乗則に従う）
    scale_invariance = float(r_squared)

    # 臨界からの距離: b=1.0が臨界
    distance_from_critical = abs(b_value - 1.0)

    if scale_invariance > 0.95 and distance_from_critical < 0.1:
        state = "critical"
    elif scale_invariance > 0.9:
        state = "near_critical"
    elif scale_invariance > 0.8:
        state = "subcritical"
    else:
        state = "non_scaling"

    return {
        "b_value": round(b_value, 3),
        "scale_invariance_r2": round(scale_invariance, 4),
        "distance_from_critical": round(distance_from_critical, 3),
        "state": state,
        "n_magnitude_bins": int(np.sum(valid)),
        "n_events": len(events),
    }
