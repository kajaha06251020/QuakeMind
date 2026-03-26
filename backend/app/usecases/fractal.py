"""フラクタル次元解析（相関次元 D2）。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)
_MIN_EVENTS = 10


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def compute_correlation_dimension(latitudes: np.ndarray, longitudes: np.ndarray) -> float | None:
    n = len(latitudes)
    if n < _MIN_EVENTS:
        return None

    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            d = _haversine_km(latitudes[i], longitudes[i], latitudes[j], longitudes[j])
            if d > 0:
                distances.append(d)

    if len(distances) < 10:
        return 0.0

    distances = np.array(distances)
    d_min = max(distances.min(), 0.01)
    d_max = distances.max()
    if d_min >= d_max:
        return 0.0

    r_values = np.logspace(np.log10(d_min), np.log10(d_max), 20)
    n_pairs = n * (n - 1) / 2

    log_r, log_c = [], []
    for r in r_values:
        count = np.sum(distances <= r)
        c_r = count / n_pairs
        if c_r > 0:
            log_r.append(np.log10(r))
            log_c.append(np.log10(c_r))

    if len(log_r) < 5:
        return 0.0

    log_r = np.array(log_r)
    log_c = np.array(log_c)
    n_pts = len(log_r)
    start = n_pts // 4
    end = 3 * n_pts // 4
    if end - start < 3:
        start, end = 0, n_pts

    x = log_r[start:end]
    y = log_c[start:end]
    if len(x) < 2:
        return 0.0

    coeffs = np.polyfit(x, y, 1)
    d2 = float(coeffs[0])
    return round(max(0.0, d2), 2)
