"""メタ認知エンジン。自分の分析の信頼性を自己評価する。"""
import logging
from datetime import datetime, timezone
from app.services.model_scoreboard import get_scoreboard
from app.services.knowledge_gaps import detect_knowledge_gaps

logger = logging.getLogger(__name__)


async def self_evaluate(events, analyses_performed=None):
    """システムの自己評価を実行する。"""
    scoreboard = get_scoreboard()
    gaps = detect_knowledge_gaps(events, analyses_performed)

    # 信頼度スコア
    confidence_factors = []

    # データ量
    n = len(events)
    data_confidence = min(1.0, n / 100)
    confidence_factors.append(("data_volume", data_confidence, f"{n}イベント（100件で満点）"))

    # モデル精度
    models = scoreboard.get("models", {})
    if models:
        avg_acc = sum(m.get("accuracy", 0.5) for m in models.values()) / len(models)
        confidence_factors.append(("model_accuracy", avg_acc, f"平均精度{avg_acc:.0%}"))
    else:
        confidence_factors.append(("model_accuracy", 0.3, "モデル評価データなし"))

    # 知識ギャップ
    gap_penalty = min(0.5, gaps.get("high_severity", 0) * 0.1)
    gap_score = 1.0 - gap_penalty
    confidence_factors.append(("knowledge_completeness", gap_score, f"高深刻度ギャップ{gaps.get('high_severity', 0)}件"))

    overall = sum(f[1] for f in confidence_factors) / len(confidence_factors)

    weaknesses = []
    for name, score, desc in confidence_factors:
        if score < 0.5:
            weaknesses.append({"area": name, "score": round(score, 2), "description": desc})

    return {
        "overall_confidence": round(overall, 4),
        "confidence_level": "high" if overall >= 0.7 else "medium" if overall >= 0.4 else "low",
        "factors": [{"name": n, "score": round(s, 4), "detail": d} for n, s, d in confidence_factors],
        "weaknesses": weaknesses,
        "recommendation": weaknesses[0]["description"] if weaknesses else "全体的に良好",
    }
