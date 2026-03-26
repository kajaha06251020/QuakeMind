"""知識ギャップ検出。データ/理解が不足している領域を自動特定する。"""
import logging
from datetime import datetime, timezone

from app.services.active_learning import identify_data_gaps
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def detect_knowledge_gaps(events: list[EarthquakeRecord], analyses_performed: dict | None = None) -> dict:
    """研究上の知識ギャップを検出する。"""
    gaps = []

    # 1. データギャップ
    data_gaps = identify_data_gaps(events)
    for g in data_gaps.get("data_gaps", []):
        if g["priority"] == "high":
            gaps.append({
                "type": "data_gap",
                "severity": "high",
                "description": f"{g['region']}: データが極端に不足（{g['event_count']}件）",
                "recommendation": f"{g['region']}のデータソースを追加するか、バルクインポートを実行してください",
            })

    # 2. モデル精度ギャップ
    if analyses_performed:
        if not analyses_performed.get("etas_evaluated"):
            gaps.append({
                "type": "model_evaluation_gap",
                "severity": "medium",
                "description": "ETASモデルの精度評価が未実施",
                "recommendation": "POST /research-dashboard/run/weekly でETAS評価を実行してください",
            })
        if not analyses_performed.get("ml_evaluated"):
            gaps.append({
                "type": "model_evaluation_gap",
                "severity": "medium",
                "description": "MLモデルの精度評価が未実施",
                "recommendation": "予測→検証サイクルを実行してモデル精度を追跡してください",
            })

    # 3. 時間的ギャップ
    if events:
        from datetime import datetime as dt
        try:
            timestamps = sorted([dt.fromisoformat(e.timestamp.replace("Z", "+00:00")) for e in events])
            span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400
            if span_days < 30:
                gaps.append({
                    "type": "temporal_gap",
                    "severity": "high",
                    "description": f"データのカバー期間が{span_days:.0f}日しかない。統計分析には最低90日推奨",
                    "recommendation": "バルクインポート（scripts/bulk_import.py）で過去データを追加してください",
                })
        except Exception:
            pass

    # 4. マグニチュードカバレッジ
    if events:
        mags = [e.magnitude for e in events]
        if max(mags) < 5.0:
            gaps.append({
                "type": "magnitude_gap",
                "severity": "medium",
                "description": "M5以上のイベントがない。大地震の予測精度を評価できない",
                "recommendation": "グローバルデータ（USGS/IRIS）をインポートして大地震のパターンを学習させてください",
            })

    # 5. 分析ギャップ
    if not analyses_performed or not analyses_performed.get("hypotheses_generated"):
        gaps.append({
            "type": "analysis_gap",
            "severity": "low",
            "description": "仮説の自動生成が未実行",
            "recommendation": "POST /advanced-prediction/generate-hypotheses で仮説生成を実行してください",
        })

    gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g["severity"], 3))

    return {
        "total_gaps": len(gaps),
        "high_severity": sum(1 for g in gaps if g["severity"] == "high"),
        "gaps": gaps,
    }
