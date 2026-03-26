"""GeoNet (New Zealand) 地震 API クライアント。"""
import logging
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    if not settings.geonet_enabled:
        return []

    params = {"MMI": -1}  # 全震度
    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.geonet_api_url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("[GeoNet] API エラー: %s", e)
        return []

    events = []
    for feature in data.get("features", [])[:limit]:
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue

            magnitude = props.get("magnitude", -1)
            if magnitude is None or magnitude < 0:
                continue

            lon, lat = float(coords[0]), float(coords[1])
            depth_km = float(coords[2]) if len(coords) > 2 else 0.0

            time_str = props.get("time", "")
            timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00")) if time_str else datetime.now(timezone.utc)

            events.append(EarthquakeEvent(
                event_id="geonet-" + props.get("publicID", str(len(events))),
                magnitude=float(magnitude),
                depth_km=depth_km,
                latitude=lat,
                longitude=lon,
                region=props.get("locality", "New Zealand"),
                timestamp=timestamp,
                source="geonet",
            ))
        except Exception as e:
            logger.warning("[GeoNet] パースエラー: %s", e)
            continue
    return events
