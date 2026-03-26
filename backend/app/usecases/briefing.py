"""日次リスクブリーフィング生成。"""
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def generate_daily_briefing(events: list[EarthquakeRecord], days: int = 1) -> dict:
    """過去N日間の地震活動サマリを生成する。LLM不要の構造化ブリーフィング。"""
    if not events:
        return {"period_days": days, "total_events": 0, "summary": "指定期間にイベントはありません。", "highlights": []}

    def _parse(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_events = sorted(events, key=_parse, reverse=True)
    cutoff = _parse(sorted_events[0]) - timedelta(days=days)
    recent = [e for e in sorted_events if _parse(e) >= cutoff]

    if not recent:
        return {"period_days": days, "total_events": 0, "summary": "指定期間にイベントはありません。", "highlights": []}

    mags = [e.magnitude for e in recent]
    max_event = max(recent, key=lambda e: e.magnitude)

    highlights = []
    if max(mags) >= 5.0:
        highlights.append(f"M{max(mags):.1f} の大きな地震が発生しました")
    if len(recent) > 10:
        highlights.append(f"活動が活発です（{len(recent)}件/{days}日）")
    if not highlights:
        highlights.append("特筆すべき活動はありません")

    return {
        "period_days": days,
        "total_events": len(recent),
        "max_magnitude": round(max(mags), 1),
        "avg_magnitude": round(sum(mags) / len(mags), 2),
        "summary": f"過去{days}日間で{len(recent)}件の地震を観測。最大M{max(mags):.1f}。",
        "highlights": highlights,
    }
