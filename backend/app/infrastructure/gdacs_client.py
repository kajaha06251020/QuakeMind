"""GDACS (Global Disaster Alert) 地震 RSS クライアント。"""
import logging
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    if not settings.gdacs_enabled:
        return []

    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.gdacs_rss_url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as e:
        logger.error("[GDACS] RSS エラー: %s", e)
        return []

    return _parse_gdacs_rss(xml_text, limit)


def _parse_gdacs_rss(xml_text: str, limit: int = 20) -> list[EarthquakeEvent]:
    """GDACS RSS XML をパースする。lxml なしの簡易パーサー。"""
    import re
    events = []

    # <item> ブロックを抽出
    items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)

    for item in items[:limit]:
        try:
            title = re.search(r"<title>(.*?)</title>", item)
            if not title:
                continue
            title_text = title.group(1)

            # マグニチュードを抽出 (例: "M 5.2")
            mag_match = re.search(r"M\s*([\d.]+)", title_text)
            if not mag_match:
                continue
            magnitude = float(mag_match.group(1))

            # 座標を抽出
            lat_match = re.search(r"<geo:lat>([\d.-]+)</geo:lat>", item)
            lon_match = re.search(r"<geo:long>([\d.-]+)</geo:long>", item)
            if not lat_match or not lon_match:
                continue
            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))

            # 日付
            pub_date = re.search(r"<pubDate>(.*?)</pubDate>", item)
            if pub_date:
                from email.utils import parsedate_to_datetime
                try:
                    timestamp = parsedate_to_datetime(pub_date.group(1)).replace(tzinfo=timezone.utc)
                except Exception:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # GDACS ID
            guid = re.search(r"<guid.*?>(.*?)</guid>", item)
            event_id = "gdacs-" + (guid.group(1).split("/")[-1] if guid else str(len(events)))

            # 説明から地域を抽出
            desc = re.search(r"<description>(.*?)</description>", item)
            region = desc.group(1)[:100] if desc else "Unknown"

            events.append(EarthquakeEvent(
                event_id=event_id,
                magnitude=magnitude,
                depth_km=0.0,  # GDACS RSS に深度情報なし
                latitude=lat,
                longitude=lon,
                region=region,
                timestamp=timestamp,
                source="gdacs",
            ))
        except Exception as e:
            logger.warning("[GDACS] パースエラー: %s", e)
            continue

    return events
