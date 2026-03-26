"""気候変動と地震活動の相関分析。"""
import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


def analyze_climate_earthquake_correlation(
    earthquake_annual_counts: np.ndarray,
    sea_level_mm: np.ndarray | None = None,
    temperature_anomaly_c: np.ndarray | None = None,
    ice_mass_gt: np.ndarray | None = None,
    years: np.ndarray | None = None,
) -> dict:
    """長期的な気候指標と地震活動の相関を分析する。"""
    n = len(earthquake_annual_counts)
    results = {"n_years": n, "correlations": {}, "trends": {}}

    # 地震活動のトレンド
    if n >= 5:
        slope, _, r, p, _ = stats.linregress(range(n), earthquake_annual_counts)
        results["trends"]["earthquake_rate"] = {
            "slope_per_year": round(float(slope), 3),
            "r_squared": round(float(r**2), 4),
            "p_value": round(float(p), 6),
            "trend": "increasing" if slope > 0 and p < 0.05 else "decreasing" if slope < 0 and p < 0.05 else "stable",
        }

    signals = {}
    if sea_level_mm is not None and len(sea_level_mm) == n: signals["sea_level"] = sea_level_mm
    if temperature_anomaly_c is not None and len(temperature_anomaly_c) == n: signals["temperature"] = temperature_anomaly_c
    if ice_mass_gt is not None and len(ice_mass_gt) == n: signals["ice_mass"] = ice_mass_gt

    for name, signal in signals.items():
        r, p = stats.pearsonr(earthquake_annual_counts, signal) if n >= 3 else (0, 1)
        results["correlations"][name] = {
            "pearson_r": round(float(r), 4),
            "p_value": round(float(p), 6),
            "significant": p < 0.05,
        }

    # 総合評価
    sig_correlations = [k for k, v in results["correlations"].items() if v.get("significant")]
    results["summary"] = {
        "significant_correlations": sig_correlations,
        "interpretation": (
            f"気候指標({', '.join(sig_correlations)})と地震活動に統計的に有意な相関が検出された。ただし相関は因果関係を意味しない。"
            if sig_correlations else
            "気候指標と地震活動の間に統計的に有意な相関は検出されなかった。"
        ),
        "caveat": "気候変動と地震の因果関係は科学的に確立されていない。相関のみでは結論を出せない。",
    }

    return results
