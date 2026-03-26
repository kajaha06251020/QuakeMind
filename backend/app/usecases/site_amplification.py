"""サイト増幅係数。Vs30地盤分類に基づく揺れの増幅。"""
import math, logging
logger = logging.getLogger(__name__)

_VS30_AMPLIFICATION = {
    "rock": {"vs30": 760, "factor": 1.0, "description": "岩盤"},
    "stiff_soil": {"vs30": 360, "factor": 1.5, "description": "硬い土"},
    "medium_soil": {"vs30": 180, "factor": 2.0, "description": "中程度の土"},
    "soft_soil": {"vs30": 90, "factor": 3.0, "description": "軟弱地盤"},
    "very_soft": {"vs30": 45, "factor": 4.5, "description": "非常に軟弱（埋立地等）"},
}

def compute_site_amplification(base_intensity: float, vs30: float = 180) -> dict:
    # Vs30から増幅係数を補間
    if vs30 >= 760: factor = 1.0
    elif vs30 >= 360: factor = 1.0 + (760 - vs30) / (760 - 360) * 0.5
    elif vs30 >= 180: factor = 1.5 + (360 - vs30) / (360 - 180) * 0.5
    elif vs30 >= 90: factor = 2.0 + (180 - vs30) / (180 - 90) * 1.0
    else: factor = 3.0 + (90 - vs30) / 90 * 1.5
    factor = min(5.0, factor)
    amplified = min(7.0, base_intensity + math.log10(factor) * 2)
    site_class = "rock" if vs30 >= 760 else "stiff_soil" if vs30 >= 360 else "medium_soil" if vs30 >= 180 else "soft_soil" if vs30 >= 90 else "very_soft"
    return {"base_intensity": round(base_intensity, 2), "vs30": vs30, "amplification_factor": round(factor, 2), "amplified_intensity": round(amplified, 2), "site_class": site_class}
