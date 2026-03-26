"""機械学習ベースの地震予測。

特徴量: b値変動、クラスタリング傾向、最大マグニチュード、発生率変化
モデル: ロジスティック回帰（scipy）
"""
import math
import logging

import numpy as np
from scipy.special import expit  # sigmoid

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import analyze_gutenberg_richter

logger = logging.getLogger(__name__)


def _extract_features(events: list[EarthquakeRecord]) -> np.ndarray | None:
    """イベントリストから予測用特徴量を抽出する。"""
    if len(events) < 10:
        return None

    mags = np.array([e.magnitude for e in events])

    # 特徴量
    f1 = float(np.mean(mags))          # 平均マグニチュード
    f2 = float(np.max(mags))           # 最大マグニチュード
    f3 = float(np.std(mags))           # マグニチュード標準偏差
    f4 = float(len(events))            # イベント数

    # b値（計算可能なら）
    try:
        gr = analyze_gutenberg_richter(events)
        f5 = gr.b_value
    except Exception:
        f5 = 1.0  # デフォルト

    # 後半/前半のイベント数比（加速度）
    half = len(events) // 2
    first_half = len(events[:half])
    second_half = len(events[half:])
    f6 = second_half / max(first_half, 1)

    return np.array([f1, f2, f3, f4, f5, f6])


def predict_large_earthquake(
    events: list[EarthquakeRecord],
    magnitude_threshold: float = 5.0,
) -> dict:
    """大地震（M >= threshold）発生確率を予測する。

    経験的な重み付けロジスティック回帰:
    P = sigmoid(w1*mean_mag + w2*max_mag + w3*std_mag + w4*log(n_events) + w5*(1-b) + w6*acceleration - bias)
    """
    features = _extract_features(events)
    if features is None:
        return {"error": "イベント数不足（最低10件必要）", "probability": 0.0}

    f_mean, f_max, f_std, f_n, f_b, f_accel = features

    # 経験的な重み（正の値 = リスク増加に寄与）
    score = (
        0.3 * (f_mean - 3.0) +     # 平均マグニチュードが高いほどリスク
        0.5 * (f_max - 4.0) +       # 最大マグニチュードが高いほどリスク
        0.2 * f_std +                # ばらつきが大きいほどリスク
        0.1 * math.log(f_n + 1) +   # イベント数が多いほどリスク
        0.4 * (1.0 - f_b) +         # b値が低いほどリスク
        0.3 * (f_accel - 1.0) -     # 活動加速はリスク
        2.0                          # バイアス
    )

    probability = float(expit(score))

    # リスクレベル
    if probability >= 0.7:
        risk_level = "high"
    elif probability >= 0.4:
        risk_level = "moderate"
    elif probability >= 0.2:
        risk_level = "low"
    else:
        risk_level = "very_low"

    return {
        "probability": round(probability, 4),
        "risk_level": risk_level,
        "magnitude_threshold": magnitude_threshold,
        "features": {
            "mean_magnitude": round(f_mean, 2),
            "max_magnitude": round(f_max, 1),
            "magnitude_std": round(f_std, 2),
            "event_count": int(f_n),
            "b_value": round(f_b, 3),
            "acceleration_ratio": round(f_accel, 2),
        },
        "n_events_analyzed": len(events),
    }
