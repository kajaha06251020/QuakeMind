"""イベント駆動トリガー。地震発生時に自動で分析を起動する。"""
import logging
from app.domain.models import EarthquakeEvent
from app.services.research_journal import add_entry

logger = logging.getLogger(__name__)

_MAGNITUDE_THRESHOLD = 5.0
_B_VALUE_DROP_THRESHOLD = -0.2


async def on_new_earthquake(event: EarthquakeEvent) -> list[str]:
    """新しい地震イベントに対してトリガーを評価する。

    Returns: 起動されたアクション名のリスト。
    """
    actions = []

    if event.magnitude >= _MAGNITUDE_THRESHOLD:
        actions.append("large_earthquake_investigation")
        logger.info("[Trigger] M%.1f 大地震検出 → 詳細分析起動: %s", event.magnitude, event.event_id)

        try:
            from app.services.research_workflow import investigate_large_earthquake
            await investigate_large_earthquake(event.event_id)
        except Exception as e:
            logger.error("[Trigger] 詳細分析エラー: %s", e)

    if event.magnitude >= 4.0:
        actions.append("anomaly_check")
        try:
            from app.services.research_scheduler import hourly_analysis
            await hourly_analysis()
        except Exception as e:
            logger.error("[Trigger] 異常検知エラー: %s", e)

    if actions:
        await add_entry(
            "finding",
            f"トリガー発火: M{event.magnitude} {event.event_id}",
            f"起動アクション: {', '.join(actions)}",
            metadata={"event_id": event.event_id, "magnitude": event.magnitude, "actions": actions},
        )

    return actions


async def on_b_value_change(region: str, old_b: float, new_b: float) -> list[str]:
    """b値変化に対してトリガーを評価する。"""
    actions = []
    change = new_b - old_b

    if change <= _B_VALUE_DROP_THRESHOLD:
        actions.append("b_value_investigation")
        logger.info("[Trigger] b値急低下 %s: %.2f → %.2f", region, old_b, new_b)

        try:
            from app.services.research_workflow import investigate_anomaly
            await investigate_anomaly(region)
        except Exception as e:
            logger.error("[Trigger] 異常調査エラー: %s", e)

    return actions
