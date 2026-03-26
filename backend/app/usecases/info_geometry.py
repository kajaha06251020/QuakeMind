"""情報幾何学。地震分布のフィッシャー情報量で変化速度を測定する。"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def fisher_information(counts_before: np.ndarray, counts_after: np.ndarray) -> float:
    if len(counts_before) < 3 or len(counts_after) < 3:
        return 0.0
    p1 = counts_before / max(counts_before.sum(), 1)
    p2 = counts_after / max(counts_after.sum(), 1)
    p1 = np.clip(p1, 1e-10, None)
    p2 = np.clip(p2, 1e-10, None)
    kl = float(np.sum(p2 * np.log(p2 / p1)))
    return max(0, kl)


def compute_distribution_change(magnitudes: np.ndarray, split_point: int = None) -> dict:
    if len(magnitudes) < 20:
        return {"error": "最低20データ点必要"}
    if split_point is None:
        split_point = len(magnitudes) // 2
    before = magnitudes[:split_point]
    after = magnitudes[split_point:]
    bins = np.arange(0, 10, 0.5)
    h_before, _ = np.histogram(before, bins=bins)
    h_after, _ = np.histogram(after, bins=bins)
    fi = fisher_information(h_before.astype(float), h_after.astype(float))

    significant = fi > 0.1
    return {
        "kl_divergence": round(fi, 6),
        "significant_change": significant,
        "before_mean": round(float(np.mean(before)), 2),
        "after_mean": round(float(np.mean(after)), 2),
        "interpretation": "分布に有意な変化あり" if significant else "分布は安定",
    }
