"""マルチソースアグリゲーター。

P2P, USGS, JMA XML の各クライアントを並列呼び出しし、
重複排除・正規化した地震イベントリストを返す。
"""
import asyncio
import logging
from datetime import timezone

from app.domain.models import EarthquakeEvent
from app.infrastructure.jma_client import fetch_recent_events as p2p_fetch
from app.infrastructure.usgs_client import fetch_recent_events as usgs_fetch
from app.infrastructure.jma_xml_client import fetch_recent_events as jma_xml_fetch

logger = logging.getLogger(__name__)

# 重複判定しきい値
_LAT_THRESHOLD = 0.5      # 度
_LON_THRESHOLD = 0.5      # 度
_MAG_THRESHOLD = 0.3      # マグニチュード差
_TIME_THRESHOLD = 120.0   # 秒


def _is_duplicate(a: EarthquakeEvent, b: EarthquakeEvent) -> bool:
    """2つのイベントが同一地震を指しているか判定する。"""
    if abs(a.latitude - b.latitude) > _LAT_THRESHOLD:
        return False
    if abs(a.longitude - b.longitude) > _LON_THRESHOLD:
        return False
    if abs(a.magnitude - b.magnitude) > _MAG_THRESHOLD:
        return False
    # timezone-aware に揃える
    ta = a.timestamp.replace(tzinfo=timezone.utc) if a.timestamp.tzinfo is None else a.timestamp
    tb = b.timestamp.replace(tzinfo=timezone.utc) if b.timestamp.tzinfo is None else b.timestamp
    if abs((ta - tb).total_seconds()) > _TIME_THRESHOLD:
        return False
    return True


def _deduplicate(events: list[EarthquakeEvent]) -> list[EarthquakeEvent]:
    """重複イベントを除去する（先に追加された高優先度イベントを優先）。"""
    result: list[EarthquakeEvent] = []
    for event in events:
        if not any(_is_duplicate(event, kept) for kept in result):
            result.append(event)
    return result


async def fetch_all_sources(limit: int = 20) -> list[EarthquakeEvent]:
    """全有効ソースを並列取得し、重複排除した統合リストを返す。
    優先順: P2P > USGS > JMA XML
    """
    # coroutine を直接 gather に渡す（create_task は不要）
    results = await asyncio.gather(
        p2p_fetch(limit=limit),
        usgs_fetch(limit=limit),
        jma_xml_fetch(limit=limit),
        return_exceptions=True,
    )

    all_events: list[EarthquakeEvent] = []
    source_names = ["p2p", "usgs", "jma_xml"]
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            logger.error("[MultiSource] %s エラー: %s", name, result)
        else:
            all_events.extend(result)
            logger.debug("[MultiSource] %s: %d 件", name, len(result))

    deduped = _deduplicate(all_events)
    logger.info("[MultiSource] 統合 %d 件（重複除去前: %d 件）", len(deduped), len(all_events))
    return deduped
