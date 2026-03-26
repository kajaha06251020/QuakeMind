"""意思決定支援システム。リスクレベルに応じた具体的なアクションを提案する。"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_recommendations(
    risk_level: str,
    unified_probability: float = 0.0,
    scenario: dict | None = None,
    region: str | None = None,
) -> dict:
    """リスクレベルに応じた意思決定支援を生成する。"""

    actions = {
        "immediate": [],     # 今すぐ実施
        "short_term": [],    # 24時間以内
        "medium_term": [],   # 1週間以内
        "monitoring": [],    # 継続監視
    }

    if risk_level == "critical":
        actions["immediate"] = [
            {"action": "全関係機関に警戒情報を発信", "priority": "urgent", "target": "防災担当"},
            {"action": "避難経路の確認と避難準備の呼びかけ", "priority": "urgent", "target": "住民"},
            {"action": "津波リスク地域の即時警戒", "priority": "urgent", "target": "沿岸部"},
        ]
        actions["short_term"] = [
            {"action": "防災備蓄の確認（水・食料・医薬品）", "priority": "high", "target": "全員"},
            {"action": "通信手段の確保（衛星電話、ラジオ）", "priority": "high", "target": "自治体"},
            {"action": "医療機関の受入体制確認", "priority": "high", "target": "医療"},
        ]
        actions["medium_term"] = [
            {"action": "広域避難計画の再確認", "priority": "medium", "target": "自治体"},
            {"action": "耐震性の低い建物のリスト更新", "priority": "medium", "target": "建築"},
        ]

    elif risk_level == "high":
        actions["short_term"] = [
            {"action": "監視体制の強化（ポーリング頻度を上げる）", "priority": "high", "target": "研究"},
            {"action": "防災備蓄の点検", "priority": "medium", "target": "全員"},
        ]
        actions["medium_term"] = [
            {"action": "避難訓練の実施検討", "priority": "medium", "target": "自治体"},
            {"action": "建物の緊急点検", "priority": "medium", "target": "建築"},
        ]
        actions["monitoring"] = [
            {"action": "b値・発生率の日次監視", "priority": "medium", "target": "研究"},
            {"action": "GNSS地殻変動の確認", "priority": "medium", "target": "研究"},
        ]

    elif risk_level == "elevated":
        actions["monitoring"] = [
            {"action": "通常より高頻度の分析実行", "priority": "low", "target": "研究"},
            {"action": "週次レポートの確認", "priority": "low", "target": "防災担当"},
        ]

    else:  # normal
        actions["monitoring"] = [
            {"action": "定期モニタリングの継続", "priority": "routine", "target": "研究"},
        ]

    # シナリオベースの追加推奨
    if scenario:
        if scenario.get("tsunami", {}).get("risk"):
            earliest = scenario["tsunami"].get("earliest_arrival_min")
            if earliest:
                actions["immediate"].append({
                    "action": f"沿岸部は{earliest:.0f}分以内に高台へ避難",
                    "priority": "urgent",
                    "target": "沿岸住民",
                })

        if scenario.get("damage", {}).get("affected_population", 0) > 100000:
            actions["short_term"].append({
                "action": f"推定{scenario['damage']['affected_population']:,}人に影響。広域支援体制の準備",
                "priority": "high",
                "target": "政府",
            })

    total_actions = sum(len(v) for v in actions.values())

    return {
        "risk_level": risk_level,
        "unified_probability": round(unified_probability, 4),
        "region": region,
        "total_actions": total_actions,
        "actions": actions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "本システムの出力は研究参考情報であり、公式の防災判断に代わるものではありません。",
    }
