"""P2P地震情報 API クライアント。"""
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


def _parse_p2p_event(raw: dict) -> Optional[EarthquakeEvent]:
    try:
        eq = raw.get("earthquake", {})
        hypo = eq.get("hypocenter", {})
        magnitude = hypo.get("magnitude", -1.0)
        latitude = hypo.get("latitude", 0.0)
        longitude = hypo.get("longitude", 0.0)
        if magnitude < 0 or latitude == 0.0:
            return None
        time_str = raw.get("time", eq.get("time", ""))
        try:
            timestamp = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.utcnow()
        return EarthquakeEvent(
            event_id=str(raw.get("id", "")),
            magnitude=float(magnitude),
            depth_km=float(hypo.get("depth", 0)),
            latitude=float(latitude),
            longitude=float(longitude),
            region=hypo.get("name", "不明"),
            timestamp=timestamp,
            source="p2p",
        )
    except Exception as e:
        logger.warning("イベントパースエラー: %s — %s", e, raw.get("id"))
        return None


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    params = {"codes": 551, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.p2p_api_url, params=params)
            resp.raise_for_status()
            raw_list = resp.json()
    except httpx.TimeoutException:
        logger.error("P2P API タイムアウト (%.1fs)", settings.jma_timeout)
        return []
    except Exception as e:
        logger.error("P2P API エラー: %s", e)
        return []
    return [e for raw in raw_list if (e := _parse_p2p_event(raw))]
