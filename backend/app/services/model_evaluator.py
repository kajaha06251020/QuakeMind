"""モデル精度の自動評価。ETAS/ML予測の的中率を追跡する。"""
import logging
from datetime import datetime, timezone

from app.services.experiment_logger import log_experiment
from app.services.research_journal import add_entry

logger = logging.getLogger(__name__)


async def evaluate_etas_accuracy(
    predictions: list[dict],  # [{"forecast_at": str, "expected_events": float, "actual_events": int}]
) -> dict:
    """ETAS 予測の精度を評価する。"""
    if not predictions:
        return {"error": "評価データなし"}

    errors = []
    for p in predictions:
        expected = p.get("expected_events", 0)
        actual = p.get("actual_events", 0)
        errors.append(abs(expected - actual))

    mae = sum(errors) / len(errors)
    rmse = (sum(e**2 for e in errors) / len(errors)) ** 0.5

    result = {
        "n_predictions": len(predictions),
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    await log_experiment("etas_evaluation", {"n_predictions": len(predictions)}, result)
    return result


async def evaluate_ml_accuracy(
    predictions: list[dict],  # [{"predicted_prob": float, "actual_occurred": bool}]
) -> dict:
    """ML予測の精度を評価する。"""
    if not predictions:
        return {"error": "評価データなし"}

    tp = sum(1 for p in predictions if p["predicted_prob"] >= 0.5 and p["actual_occurred"])
    fp = sum(1 for p in predictions if p["predicted_prob"] >= 0.5 and not p["actual_occurred"])
    fn = sum(1 for p in predictions if p["predicted_prob"] < 0.5 and p["actual_occurred"])
    tn = sum(1 for p in predictions if p["predicted_prob"] < 0.5 and not p["actual_occurred"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(predictions)

    result = {
        "n_predictions": len(predictions),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    await log_experiment("ml_evaluation", {"n_predictions": len(predictions)}, result)
    return result
