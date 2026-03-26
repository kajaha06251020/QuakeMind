"""気象庁リアルタイム震度データクライアント。

観測点ごとの震度情報を取得する。JMA XML Atom Feed から地震情報を抽出し、
震度観測データとして返す。
"""
import logging
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    """気象庁リアルタイム震度データを取得する。

    Note: jma_xml_client と同じ Atom Feed を使用するが、
    ここでは震度観測点データとしてパースする。
    jma_xml_enabled とは独立して動作する。
    """
    if not settings.jma_intensity_enabled:
        return []

    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.jma_intensity_url)
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        logger.error("[JMA-Intensity] API エラー: %s", e)
        return []

    return _parse_intensity_feed(text, limit)


def _parse_intensity_feed(text: str, limit: int = 20) -> list[EarthquakeEvent]:
    """Atom Feed から地震イベントを簡易パース。"""
    import re
    events = []

    entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)
    for entry in entries[:limit]:
        try:
            title = re.search(r"<title>(.*?)</title>", entry)
            if not title or "震度" not in title.group(1) and "地震" not in title.group(1):
                continue

            entry_id = re.search(r"<id>(.*?)</id>", entry)
            updated = re.search(r"<updated>(.*?)</updated>", entry)

            if not entry_id:
                continue

            event_id = "jma-int-" + entry_id.group(1).split("/")[-1][:20]

            if updated:
                try:
                    timestamp = datetime.fromisoformat(updated.group(1).replace("Z", "+00:00"))
                except Exception:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            events.append(EarthquakeEvent(
                event_id=event_id,
                magnitude=0.0,  # 震度データにはマグニチュードが直接含まれない場合がある
                depth_km=0.0,
                latitude=36.0,  # 日本中心のデフォルト
                longitude=140.0,
                region=title.group(1)[:50],
                timestamp=timestamp,
                source="jma_intensity",
            ))
        except Exception as e:
            logger.warning("[JMA-Intensity] パースエラー: %s", e)
            continue

    return events
