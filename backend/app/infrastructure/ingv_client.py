"""INGV FDSN API クライアント。"""
import logging
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)

_JAPAN_BBOX = [24.0, 46.0, 122.0, 154.0]  # min_lat, max_lat, min_lon, max_lon


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    if not settings.ingv_enabled:
        return []

    min_lat, max_lat, min_lon, max_lon = _JAPAN_BBOX
    params = {
        "format": "text",
        "minmagnitude": settings.magnitude_threshold,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "limit": limit,
        "orderby": "time",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.ingv_api_url, params=params)
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        logger.error("[INGV] API エラー: %s", e)
        return []

    return _parse_fdsn_text(text)


def _parse_fdsn_text(text: str) -> list[EarthquakeEvent]:
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("#") or line.startswith("EventID"):
            continue
        parts = line.split("|")
        if len(parts) < 11:
            continue
        try:
            event_id = "ingv-" + parts[0].strip()
            timestamp = datetime.fromisoformat(parts[1].strip().replace("Z", "+00:00"))
            latitude = float(parts[2].strip())
            longitude = float(parts[3].strip())
            depth_km = float(parts[4].strip()) if parts[4].strip() else 0.0
            magnitude = float(parts[10].strip()) if parts[10].strip() else float(parts[9].strip()) if parts[9].strip() else -1.0

            if magnitude < 0:
                continue

            events.append(EarthquakeEvent(
                event_id=event_id,
                magnitude=magnitude,
                depth_km=depth_km,
                latitude=latitude,
                longitude=longitude,
                region=parts[12].strip() if len(parts) > 12 else "Unknown",
                timestamp=timestamp,
                source="ingv",
            ))
        except Exception as e:
            logger.warning("[INGV] パースエラー: %s", e)
            continue
    return events
