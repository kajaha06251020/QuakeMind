"""矛盾解決エンジン。モデル間の予測矛盾を検出し解決する。"""
import logging

logger = logging.getLogger(__name__)


def detect_contradictions(predictions: dict[str, dict]) -> list[dict]:
    """複数モデルの予測間の矛盾を検出する。"""
    contradictions = []
    models = list(predictions.keys())

    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            m1, m2 = models[i], models[j]
            p1 = predictions[m1].get("probability", 0)
            p2 = predictions[m2].get("probability", 0)

            diff = abs(p1 - p2)
            if diff > 0.3:  # 30%以上の乖離は矛盾
                # どちらが信頼できるか推論
                r1 = predictions[m1].get("reliability", 0.5)
                r2 = predictions[m2].get("reliability", 0.5)

                if r1 > r2:
                    preferred = m1
                    reason = f"{m1}の方が信頼性が高い（{r1:.2f} vs {r2:.2f}）"
                elif r2 > r1:
                    preferred = m2
                    reason = f"{m2}の方が信頼性が高い（{r2:.2f} vs {r1:.2f}）"
                else:
                    preferred = "uncertain"
                    reason = "信頼性が同等。追加データが必要"

                contradictions.append({
                    "model_a": m1,
                    "model_b": m2,
                    "prediction_a": round(p1, 4),
                    "prediction_b": round(p2, 4),
                    "divergence": round(diff, 4),
                    "preferred_model": preferred,
                    "resolution_reason": reason,
                    "severity": "high" if diff > 0.5 else "medium",
                })

    return contradictions


def resolve_and_explain(predictions: dict[str, dict]) -> dict:
    """矛盾を検出し、統合された判断を生成する。"""
    contradictions = detect_contradictions(predictions)

    # 信頼性加重平均
    total_weight = 0
    weighted_prob = 0
    for name, pred in predictions.items():
        r = pred.get("reliability", 0.5)
        p = pred.get("probability", 0)
        weighted_prob += p * r
        total_weight += r

    consensus = weighted_prob / max(total_weight, 0.01)

    return {
        "consensus_probability": round(consensus, 4),
        "n_contradictions": len(contradictions),
        "contradictions": contradictions,
        "model_count": len(predictions),
        "agreement_level": "high" if not contradictions else "low" if any(c["severity"] == "high" for c in contradictions) else "moderate",
    }
