"""有限断層モデル。点震源ではなく、断層面の滑り分布を推定する。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)


def estimate_fault_geometry(magnitude: float, depth_km: float, rake: float = 90.0) -> dict:
    """マグニチュードから断層の幾何学パラメータを推定する。
    Wells & Coppersmith (1994) + Blaser et al. (2010)。
    """
    # 破壊面積: log10(A) = -3.49 + 0.91*M
    log_area = -3.49 + 0.91 * magnitude
    area_km2 = 10 ** log_area

    # 破壊長さ: log10(L) = -2.44 + 0.59*M
    log_length = -2.44 + 0.59 * magnitude
    length_km = 10 ** log_length

    # 幅
    width_km = area_km2 / max(length_km, 0.1)

    # 平均滑り量: log10(D) = -4.80 + 0.69*M (Wells & Coppersmith)
    log_slip = -4.80 + 0.69 * magnitude
    avg_slip_m = 10 ** log_slip

    # モーメント
    mu = 3.0e10  # 剛性率 (Pa)
    moment = mu * area_km2 * 1e6 * avg_slip_m  # N*m

    return {
        "magnitude": magnitude,
        "rupture_length_km": round(length_km, 2),
        "rupture_width_km": round(width_km, 2),
        "rupture_area_km2": round(area_km2, 2),
        "average_slip_m": round(avg_slip_m, 3),
        "max_slip_m": round(avg_slip_m * 2.0, 3),  # 経験的: max ≈ 2 * avg
        "seismic_moment_nm": round(moment, 2),
        "depth_km": depth_km,
        "rake": rake,
    }


def generate_slip_distribution(
    length_km: float, width_km: float, avg_slip_m: float,
    nx: int = 20, ny: int = 10,
) -> dict:
    """断層面上の滑り分布を生成する（楕円分布モデル）。"""
    x = np.linspace(-length_km / 2, length_km / 2, nx)
    y = np.linspace(0, width_km, ny)
    X, Y = np.meshgrid(x, y)

    # 楕円状の滑り分布（中心が最大）
    a = length_km / 2
    b = width_km / 2
    r = np.sqrt((X / a) ** 2 + ((Y - width_km / 2) / b) ** 2)
    slip = avg_slip_m * 2 * np.maximum(0, 1 - r ** 2)

    return {
        "nx": nx, "ny": ny,
        "length_km": round(length_km, 2),
        "width_km": round(width_km, 2),
        "max_slip_m": round(float(np.max(slip)), 3),
        "avg_slip_m": round(float(np.mean(slip)), 3),
        "slip_grid": slip.tolist(),
    }
