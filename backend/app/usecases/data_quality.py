"""データソース品質スコアリング。"""
import logging
from datetime import datetime, timedelta, timezone

from app.infrastructure.multi_source import get_source_status

logger = logging.getLogger(__name__)


def score_data_sources() -> dict:
    """各データソースの品質スコアを計算する。

    スコアリング基準:
    - エラーなし: 100点
    - 最終エラーあり: 50点
    - ステータス未取得: 0点
    - disabled: N/A
    """
    raw = get_source_status()

    scores = {}
    for name, status in raw.items():
        last_error = status.get("last_error")
        last_fetch = status.get("last_fetch_at")

        if last_fetch is None:
            scores[name] = {"score": 0, "status": "no_data", "last_fetch_at": None, "last_error": None}
            continue

        # 鮮度チェック: 10分以上前なら減点
        score = 100
        if last_error is not None:
            score = 50

        try:
            fetch_time = datetime.fromisoformat(last_fetch)
            age_minutes = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 60
            if age_minutes > 10:
                score -= min(30, int(age_minutes / 10) * 5)
        except Exception:
            pass

        scores[name] = {
            "score": max(0, score),
            "status": "healthy" if score >= 80 else "degraded" if score >= 50 else "unhealthy",
            "last_fetch_at": last_fetch,
            "last_error": last_error,
        }

    # 全体スコア
    if scores:
        active_scores = [s["score"] for s in scores.values() if s["status"] != "no_data"]
        overall = round(sum(active_scores) / len(active_scores), 1) if active_scores else 0
    else:
        overall = 0

    return {"overall_score": overall, "sources": scores}
