"""応力反転。複数の震源メカニズム解から地域の応力場を推定する。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)


def invert_stress_field(focal_mechanisms: list[dict]) -> dict:
    """震源メカニズム解のリストから主応力方向を推定する。

    Michael (1984) の線形反転法の簡易版。
    各メカニズムの T軸/P軸/N軸 から統計的に主応力方向を推定。

    Args:
        focal_mechanisms: [{"strike": float, "dip": float, "rake": float}, ...]
    """
    if len(focal_mechanisms) < 3:
        return {"error": "最低3つの震源メカニズムが必要"}

    t_axes = []  # 引張軸
    p_axes = []  # 圧縮軸

    for fm in focal_mechanisms:
        strike = math.radians(fm.get("strike", 0))
        dip = math.radians(fm.get("dip", 45))
        rake = math.radians(fm.get("rake", 0))

        # T軸とP軸の方位角（簡易計算）
        t_az = strike + math.pi / 4  # T軸 ≈ strike + 45°
        p_az = strike - math.pi / 4  # P軸 ≈ strike - 45°

        t_axes.append([math.cos(t_az), math.sin(t_az)])
        p_axes.append([math.cos(p_az), math.sin(p_az)])

    t_axes = np.array(t_axes)
    p_axes = np.array(p_axes)

    # 平均方向（円環統計）
    t_mean = np.mean(t_axes, axis=0)
    p_mean = np.mean(p_axes, axis=0)

    t_azimuth = math.degrees(math.atan2(t_mean[1], t_mean[0])) % 360
    p_azimuth = math.degrees(math.atan2(p_mean[1], p_mean[0])) % 360

    # 応力比 R = (σ1 - σ2) / (σ1 - σ3)
    t_variance = float(np.var(np.arctan2(t_axes[:, 1], t_axes[:, 0])))
    stress_ratio = max(0.0, min(1.0, 1.0 - t_variance * 2))

    # 応力レジーム判定
    avg_rake = np.mean([fm.get("rake", 0) for fm in focal_mechanisms])
    if -30 <= avg_rake <= 30 or 150 <= avg_rake <= 210:
        regime = "strike_slip"
    elif 30 < avg_rake < 150:
        regime = "reverse"  # 逆断層（圧縮場）
    else:
        regime = "normal"  # 正断層（伸張場）

    return {
        "n_mechanisms": len(focal_mechanisms),
        "sigma1_azimuth": round(p_azimuth, 1),  # σ1 = 最大圧縮応力 = P軸方向
        "sigma3_azimuth": round(t_azimuth, 1),   # σ3 = 最小圧縮応力 = T軸方向
        "stress_ratio_R": round(stress_ratio, 3),
        "tectonic_regime": regime,
        "variance": round(t_variance, 4),
    }
