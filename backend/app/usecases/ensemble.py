"""マルチモデルアンサンブル + ベイズモデル平均（BMA）。

ETAS、ML、クーロンの予測を統合し、各モデルの信頼性で重み付け。
"""
import math
import logging

import numpy as np

logger = logging.getLogger(__name__)


def bayesian_model_averaging(
    model_predictions: list[dict],
) -> dict:
    """ベイズモデル平均で複数モデルの予測を統合する。

    Args:
        model_predictions: [{"name": str, "probability": float, "weight": float, "uncertainty": float}, ...]

    Returns:
        統合された予測 + 各モデルの寄与度
    """
    if not model_predictions:
        return {"error": "モデル予測がありません"}

    # 重みの正規化
    weights = np.array([m.get("weight", 1.0) for m in model_predictions])
    total_weight = weights.sum()
    if total_weight == 0:
        weights = np.ones(len(model_predictions)) / len(model_predictions)
    else:
        weights = weights / total_weight

    # 加重平均
    probs = np.array([m.get("probability", 0.0) for m in model_predictions])
    ensemble_prob = float(np.dot(weights, probs))

    # 不確実性の伝播
    uncertainties = np.array([m.get("uncertainty", 0.1) for m in model_predictions])
    # BMA分散 = Σ wi * (σi² + (μi - μ_ensemble)²)
    ensemble_var = float(np.dot(weights, uncertainties ** 2 + (probs - ensemble_prob) ** 2))
    ensemble_std = math.sqrt(ensemble_var)

    # 95% 信頼区間
    ci_lower = max(0, ensemble_prob - 1.96 * ensemble_std)
    ci_upper = min(1, ensemble_prob + 1.96 * ensemble_std)

    contributions = []
    for m, w in zip(model_predictions, weights):
        contributions.append({
            "model": m["name"],
            "prediction": round(m.get("probability", 0.0), 4),
            "weight": round(float(w), 4),
            "contribution": round(float(w * m.get("probability", 0.0)), 4),
        })

    return {
        "ensemble_probability": round(ensemble_prob, 4),
        "uncertainty": round(ensemble_std, 4),
        "ci_95": {"lower": round(ci_lower, 4), "upper": round(ci_upper, 4)},
        "n_models": len(model_predictions),
        "model_contributions": contributions,
    }


def update_model_weights(
    current_weights: dict[str, float],
    model_name: str,
    predicted: float,
    actual: bool,
    learning_rate: float = 0.1,
) -> dict[str, float]:
    """予測結果に基づいてモデルの重みをベイズ更新する。

    尤度: P(data|model) ∝ pred^actual * (1-pred)^(1-actual)
    """
    weights = current_weights.copy()

    if model_name not in weights:
        weights[model_name] = 1.0

    # ベルヌーイ尤度
    pred = max(0.01, min(0.99, predicted))
    if actual:
        likelihood = pred
    else:
        likelihood = 1 - pred

    # ベイズ更新
    weights[model_name] *= likelihood ** learning_rate

    # 正規化
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}

    return weights
