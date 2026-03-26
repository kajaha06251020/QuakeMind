"""自己改善ループ。予測→検証→モデル重み更新のサイクル。"""
import logging
from datetime import datetime, timezone

from app.usecases.ensemble import update_model_weights
from app.services.research_journal import add_entry
from app.services.experiment_logger import log_experiment

logger = logging.getLogger(__name__)

# 永続的なモデル重み（メモリ内。本番ではDBに保存）
_model_weights: dict[str, float] = {"etas": 0.4, "ml": 0.3, "anomaly": 0.3}


def get_model_weights() -> dict[str, float]:
    return _model_weights.copy()


async def record_prediction(model_name: str, predicted_prob: float, event_context: dict) -> str:
    """予測を記録する。後で検証に使う。"""
    return await log_experiment(
        f"prediction_{model_name}",
        {"predicted_prob": predicted_prob, **event_context},
        {"status": "pending_verification"},
    )


async def verify_and_update(model_name: str, predicted_prob: float, actual_occurred: bool) -> dict:
    """予測を検証し、モデル重みを更新する。"""
    global _model_weights

    old_weight = _model_weights.get(model_name, 0.33)
    _model_weights = update_model_weights(_model_weights, model_name, predicted_prob, actual_occurred)
    new_weight = _model_weights.get(model_name, 0.33)

    # 結果をジャーナルに記録
    accuracy_str = "的中" if (predicted_prob >= 0.5) == actual_occurred else "外れ"
    await add_entry(
        "hypothesis_update",
        f"モデル検証: {model_name} — {accuracy_str}",
        f"予測: {predicted_prob:.2f}, 実際: {'発生' if actual_occurred else '未発生'}, 重み: {old_weight:.3f} → {new_weight:.3f}",
        metadata={"model": model_name, "predicted": predicted_prob, "actual": actual_occurred, "weight_change": round(new_weight - old_weight, 4)},
    )

    await log_experiment(
        "model_weight_update",
        {"model": model_name, "predicted": predicted_prob, "actual": actual_occurred},
        {"old_weight": old_weight, "new_weight": new_weight},
    )

    return {
        "model": model_name,
        "accuracy": accuracy_str,
        "old_weight": round(old_weight, 4),
        "new_weight": round(new_weight, 4),
        "all_weights": {k: round(v, 4) for k, v in _model_weights.items()},
    }


def get_improvement_summary() -> dict:
    """自己改善の現状サマリを返す。"""
    return {
        "current_weights": {k: round(v, 4) for k, v in _model_weights.items()},
        "description": "ベイズオンライン学習でモデル重みを自動更新中。予測の的中/外れに応じて各モデルの信頼性を調整。",
    }
