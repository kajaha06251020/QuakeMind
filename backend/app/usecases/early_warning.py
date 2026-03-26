"""地震早期警報アルゴリズム。P波初動からマグニチュード推定。"""
import math, logging
import numpy as np
logger = logging.getLogger(__name__)

def estimate_from_p_wave(p_amplitude: float, p_period: float, station_distance_km: float = 100) -> dict:
    """P波の振幅と周期からマグニチュード・震度を推定する。"""
    # Nakamura (1988) 方式: M = log10(A*T) + f(R)
    if p_amplitude <= 0 or p_period <= 0: return {"error": "無効な入力"}
    log_at = math.log10(p_amplitude * p_period)
    distance_correction = 1.73 * math.log10(max(station_distance_km, 1)) + 0.83
    estimated_magnitude = log_at + distance_correction
    estimated_magnitude = max(1, min(9, estimated_magnitude))
    # S波到達までの時間
    vp, vs = 6.0, 3.5  # km/s
    p_travel = station_distance_km / vp
    s_travel = station_distance_km / vs
    warning_time = s_travel - p_travel
    # 予測震度
    R = station_distance_km
    intensity = 2.68 + 1.0*estimated_magnitude - 1.58*math.log10(max(R,1))
    return {"estimated_magnitude": round(estimated_magnitude,1), "estimated_intensity": round(max(0,min(7,intensity)),1), "warning_time_seconds": round(warning_time,1), "s_wave_arrival_seconds": round(s_travel,1), "confidence": "low" if station_distance_km > 200 else "medium" if station_distance_km > 50 else "high"}
