"""地震波エネルギー分配解析。高周波/低周波比から破壊特性を推定。"""
import logging
import numpy as np
logger = logging.getLogger(__name__)

def analyze_energy_partition(magnitudes: list[float], stress_drops_bar: list[float] | None = None) -> dict:
    if len(magnitudes) < 5: return {"error": "最低5イベント必要"}
    mags = np.array(magnitudes)
    # エネルギー推定: log10(E) = 1.5*M + 4.8 (Gutenberg-Richter)
    energies = 10**(1.5*mags+4.8)
    total_energy = float(np.sum(energies))
    # 最大イベントのエネルギー占有率
    max_fraction = float(np.max(energies) / total_energy)
    # バス則: 最大余震 ≈ M_main - 1.2
    sorted_mags = sorted(mags, reverse=True)
    if len(sorted_mags) >= 2:
        bath_diff = sorted_mags[0] - sorted_mags[1]
    else:
        bath_diff = 0
    return {"n_events": len(magnitudes), "total_energy_joules": round(total_energy,0), "max_event_energy_fraction": round(max_fraction,4), "bath_law_difference": round(bath_diff,2), "bath_law_expected": 1.2, "energy_dominated_by_largest": max_fraction > 0.9}
