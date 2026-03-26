"""不確実性の分解。認識論的（データ不足）vs 偶然的（本質的ランダム性）を分離する。"""
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def decompose_uncertainty(events: list[EarthquakeRecord], prediction_std: float = 0.15) -> dict:
    if len(events) < 10:
        return {"error": "イベント数不足"}

    n = len(events)
    mags = np.array([e.magnitude for e in events])

    # 偶然的不確実性（データ量に依存しない、地震の本質的ランダム性）
    aleatory = float(np.std(mags)) / max(float(np.mean(mags)), 1)
    aleatory = min(1.0, aleatory)

    # 認識論的不確実性（データ量で減少する）
    epistemic = 1.0 / np.sqrt(n) * 3  # 3はスケーリング定数
    epistemic = min(1.0, epistemic)

    # 総不確実性
    total = np.sqrt(aleatory**2 + epistemic**2)

    # 改善可能性
    improvable_fraction = epistemic / max(total, 0.01)
    n_needed_for_halving = int(n * 3)  # 認識論的を半分にするのに必要な追加データ

    return {
        "total_uncertainty": round(float(total), 4),
        "aleatory_uncertainty": round(float(aleatory), 4),
        "epistemic_uncertainty": round(float(epistemic), 4),
        "aleatory_fraction": round(float(aleatory / max(total, 0.01)), 4),
        "epistemic_fraction": round(float(improvable_fraction), 4),
        "improvable": round(float(improvable_fraction), 4),
        "n_events": n,
        "n_needed_to_halve_epistemic": n_needed_for_halving,
        "interpretation": (
            f"不確実性の{improvable_fraction:.0%}はデータ不足が原因。{n_needed_for_halving}件の追加データで半減可能。"
            if improvable_fraction > 0.3 else
            f"不確実性の大部分({1-improvable_fraction:.0%})は地震の本質的ランダム性。データ追加での改善は限定的。"
        ),
    }
