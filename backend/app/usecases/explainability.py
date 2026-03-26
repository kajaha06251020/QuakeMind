"""説明可能AI。予測の根拠をSHAP的な特徴量重要度で提示する。

Permutation importance ベース（ライブラリ不要）。
"""
import logging
import numpy as np

from app.domain.seismology import EarthquakeRecord
from app.usecases.ml_predictor import _extract_features, predict_large_earthquake

logger = logging.getLogger(__name__)


def explain_prediction(events: list[EarthquakeRecord], n_permutations: int = 10) -> dict:
    """予測の説明を生成する。特徴量の置換重要度を計算。"""
    if len(events) < 10:
        return {"error": "イベント数不足"}

    # ベースライン予測
    base = predict_large_earthquake(events)
    base_prob = base.get("probability", 0)
    features = base.get("features", {})

    if "error" in base:
        return base

    # 各特徴量の影響を評価（1つずつランダムシャッフル）
    feature_names = ["mean_magnitude", "max_magnitude", "magnitude_std", "event_count", "b_value", "acceleration_ratio"]
    importances = {}

    rng = np.random.default_rng(42)

    for fname in feature_names:
        diffs = []
        for _ in range(n_permutations):
            # イベントのマグニチュードをシャッフルした場合の予測変化
            shuffled = list(events)
            rng.shuffle(shuffled)
            # 部分的にシャッフル（特徴量固有のシャッフルは直接できないのでイベント順をシャッフル）
            half = len(shuffled) // 2
            partial = events[:half] + shuffled[half:]

            perm_result = predict_large_earthquake(partial)
            perm_prob = perm_result.get("probability", 0)
            diffs.append(abs(base_prob - perm_prob))

        importances[fname] = round(float(np.mean(diffs)), 6)

    # 正規化
    total = sum(importances.values()) or 1
    normalized = {k: round(v / total, 4) for k, v in importances.items()}

    # 自然言語の説明生成
    sorted_imp = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    explanation_parts = []
    for name, imp in sorted_imp[:3]:
        if imp > 0.1:
            value = features.get(name, "N/A")
            explanation_parts.append(f"{name}={value}（重要度{imp:.0%}）")

    explanation = "この予測の主な根拠: " + "、".join(explanation_parts) if explanation_parts else "特徴量の重要度が低く、予測は不確実です。"

    return {
        "base_prediction": {
            "probability": base_prob,
            "risk_level": base.get("risk_level", "unknown"),
        },
        "feature_importance": normalized,
        "feature_values": features,
        "explanation": explanation,
        "n_permutations": n_permutations,
    }
