"""震源スペクトル解析。Bruneモデルフィッティング。"""
import math, logging
import numpy as np
logger = logging.getLogger(__name__)

def fit_brune_spectrum(magnitude: float, distance_km: float = 100) -> dict:
    """Bruneモデルのスペクトルパラメータを推定する。"""
    moment = 10**(1.5*magnitude+9.05)
    # コーナー周波数: fc = 4.9e6 * Vs * (Δσ/M0)^(1/3)
    vs = 3500  # m/s
    stress_drop = 3e6  # 3 MPa (typical)
    fc = 4.9e6 * vs * (stress_drop/moment)**(1/3)
    # Bruneスペクトル
    freqs = np.logspace(-1, 2, 50)
    spectrum = moment / (1 + (freqs/fc)**2)
    log_spectrum = np.log10(np.maximum(spectrum, 1e-30))
    return {"magnitude": magnitude, "seismic_moment": moment, "corner_frequency_hz": round(float(fc),4), "stress_drop_mpa": 3.0, "spectrum": [{"freq_hz": round(float(f),3), "amplitude_log10": round(float(a),2)} for f,a in zip(freqs[::5],log_spectrum[::5])]}
