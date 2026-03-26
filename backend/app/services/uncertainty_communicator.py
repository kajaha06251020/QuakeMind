"""不確実性コミュニケーター。確率予測を対象者に合わせた言葉に翻訳する。"""
import logging

logger = logging.getLogger(__name__)


def communicate_risk(
    probability: float,
    magnitude_threshold: float = 5.0,
    timeframe: str = "7日間",
    audience: str = "general",  # "expert" | "general" | "policymaker"
) -> dict:
    """確率予測を対象者に適した表現に翻訳する。"""

    messages = {}

    # 専門家向け
    messages["expert"] = {
        "text": f"M{magnitude_threshold}以上の発生確率: {probability:.2%} ({timeframe})",
        "detail": f"ポアソン過程仮定下の超過確率。95%信頼区間は別途参照。",
        "action": "モデル出力を精査し、追加分析の要否を判断してください。",
    }

    # 一般市民向け
    if probability >= 0.5:
        general_text = f"今後{timeframe}で大きな地震が起きる可能性が**非常に高く**なっています。避難の準備をしてください。"
        urgency = "critical"
    elif probability >= 0.3:
        general_text = f"今後{timeframe}で大きな地震が起きる可能性が**高まって**います。防災グッズの確認をしてください。"
        urgency = "high"
    elif probability >= 0.1:
        general_text = f"今後{timeframe}で大きな地震が起きる可能性は**やや高い**です。日頃の備えを見直しましょう。"
        urgency = "elevated"
    elif probability >= 0.03:
        general_text = f"今後{timeframe}の地震リスクは**通常より少し高い**程度です。"
        urgency = "advisory"
    else:
        general_text = f"今後{timeframe}の地震リスクは**通常レベル**です。"
        urgency = "normal"

    messages["general"] = {"text": general_text, "urgency": urgency}

    # 政策立案者向け
    if probability >= 0.3:
        policy_text = f"リスクレベルが上昇（{probability:.1%}）。防災対応のエスカレーションを検討してください。"
        policy_action = "警戒態勢の引き上げ、避難所の準備点検、関係機関への事前通知"
    elif probability >= 0.1:
        policy_text = f"注意レベル（{probability:.1%}）。監視体制の強化を推奨します。"
        policy_action = "情報収集の強化、防災計画の確認"
    else:
        policy_text = f"通常レベル（{probability:.1%}）。定期的な防災点検を継続してください。"
        policy_action = "通常業務の継続"

    messages["policymaker"] = {"text": policy_text, "recommended_action": policy_action}

    target = messages.get(audience, messages["general"])

    return {
        "probability": round(probability, 4),
        "magnitude_threshold": magnitude_threshold,
        "timeframe": timeframe,
        "audience": audience,
        "message": target,
        "all_audiences": messages,
        "disclaimer": "この情報は研究参考値です。公式の防災情報は気象庁の発表をご確認ください。",
    }
