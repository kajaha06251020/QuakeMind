"""リアルタイムモデル競争スコアボード。"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# モデルごとのスコア履歴（メモリ内）
_scores: dict[str, list[dict]] = {}


def record_score(model_name: str, predicted: float, actual: bool) -> None:
    """予測結果を記録する。"""
    if model_name not in _scores:
        _scores[model_name] = []

    correct = (predicted >= 0.5) == actual
    _scores[model_name].append({
        "predicted": predicted,
        "actual": actual,
        "correct": correct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_scoreboard() -> dict:
    """モデルスコアボードを返す。"""
    board = {}

    for model, scores in _scores.items():
        n = len(scores)
        if n == 0:
            continue

        correct = sum(1 for s in scores if s["correct"])
        accuracy = correct / n

        # 直近10件の精度
        recent = scores[-10:]
        recent_correct = sum(1 for s in recent if s["correct"])
        recent_accuracy = recent_correct / len(recent) if recent else 0

        # Brier Score
        brier = sum((s["predicted"] - (1 if s["actual"] else 0)) ** 2 for s in scores) / n

        board[model] = {
            "total_predictions": n,
            "accuracy": round(accuracy, 4),
            "recent_accuracy_10": round(recent_accuracy, 4),
            "brier_score": round(brier, 4),
            "correct": correct,
            "last_prediction": scores[-1] if scores else None,
        }

    # ランキング
    ranked = sorted(board.items(), key=lambda x: x[1]["accuracy"], reverse=True)

    return {
        "models": board,
        "ranking": [{"rank": i + 1, "model": name, "accuracy": data["accuracy"]} for i, (name, data) in enumerate(ranked)],
        "leader": ranked[0][0] if ranked else None,
    }


def clear_scores() -> None:
    """スコアをクリア（テスト用）。"""
    _scores.clear()
