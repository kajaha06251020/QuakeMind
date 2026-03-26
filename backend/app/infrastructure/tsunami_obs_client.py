"""津波観測リアルタイムデータクライアント。

気象庁の津波関連 XML データから津波観測情報を取得する。
"""
import logging
from datetime import datetime, timezone
import re
import httpx
from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    if not settings.tsunami_obs_enabled:
        return []

    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.tsunami_obs_url)
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        logger.error("[Tsunami-Obs] API エラー: %s", e)
        return []

    return _parse_tsunami_feed(text, limit)


def _parse_tsunami_feed(text: str, limit: int = 20) -> list[EarthquakeEvent]:
    events = []
    entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)

    for entry in entries[:limit]:
        try:
            title = re.search(r"<title>(.*?)</title>", entry)
            if not title or "津波" not in title.group(1):
                continue

            entry_id = re.search(r"<id>(.*?)</id>", entry)
            updated = re.search(r"<updated>(.*?)</updated>", entry)

            if not entry_id:
                continue

            event_id = "tsunami-" + entry_id.group(1).split("/")[-1][:20]

            if updated:
                try:
                    timestamp = datetime.fromisoformat(updated.group(1).replace("Z", "+00:00"))
                except Exception:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            events.append(EarthquakeEvent(
                event_id=event_id,
                magnitude=0.0,
                depth_km=0.0,
                latitude=36.0,
                longitude=140.0,
                region=title.group(1)[:50],
                timestamp=timestamp,
                source="tsunami_obs",
            ))
        except Exception as e:
            logger.warning("[Tsunami-Obs] パースエラー: %s", e)
            continue

    return events
