"""研究戦略の自動最適化。どの分析を優先すべきかを推薦する。"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def recommend_research_strategy(
    knowledge_gaps: dict,
    recent_findings: list[dict] | None = None,
    model_scoreboard: dict | None = None,
) -> dict:
    """最適な研究戦略を推薦する。"""
    actions = []

    # 知識ギャップから優先アクションを導出
    for gap in knowledge_gaps.get("gaps", []):
        priority = 10 if gap["severity"] == "high" else 5 if gap["severity"] == "medium" else 1
        actions.append({
            "action": gap["recommendation"],
            "reason": gap["description"],
            "priority": priority,
            "category": gap["type"],
        })

    # モデルスコアボードからモデル改善提案
    if model_scoreboard and model_scoreboard.get("models"):
        for model_name, data in model_scoreboard["models"].items():
            if data.get("accuracy", 1.0) < 0.5:
                actions.append({
                    "action": f"{model_name}モデルのパラメータ再調整が必要",
                    "reason": f"精度{data['accuracy']:.0%}が50%を下回っている",
                    "priority": 8,
                    "category": "model_improvement",
                })

    # 最近の発見から研究方向を提案
    if recent_findings:
        anomaly_findings = [f for f in recent_findings if f.get("entry_type") == "anomaly"]
        if anomaly_findings:
            actions.append({
                "action": "異常活動のフォローアップ調査を実施",
                "reason": f"直近{len(anomaly_findings)}件の異常を検出。深掘り分析が必要",
                "priority": 9,
                "category": "investigation",
            })

    # デフォルトの定期タスク
    actions.append({
        "action": "週次ETAS パラメータ再推定を実行",
        "reason": "モデルを最新データに適合させるため",
        "priority": 3,
        "category": "routine",
    })
    actions.append({
        "action": "arXiv論文サーベイを実行",
        "reason": "最新の研究手法を取り込むため",
        "priority": 2,
        "category": "literature",
    })

    # 優先度順ソート
    actions.sort(key=lambda a: a["priority"], reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_actions": len(actions),
        "top_priority": actions[0] if actions else None,
        "action_plan": actions[:10],  # トップ10
    }
