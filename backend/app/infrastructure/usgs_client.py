"""USGS Earthquake Catalog API クライアント。

エンドポイント: https://earthquake.usgs.gov/fdsnws/event/1/query
フォーマット: GeoJSON
対象エリア: 日本周辺（緯度 24-46°N, 経度 122-154°E）
"""
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


def _parse_feature(feature: dict) -> EarthquakeEvent | None:
    try:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])

        magnitude = props.get("mag", -1.0)
        if magnitude is None or magnitude < 0:
            return None

        if len(coords) < 2:
            return None
        lon, lat = float(coords[0]), float(coords[1])
        depth_km = float(coords[2]) if len(coords) > 2 else 0.0

        if lat == 0.0 and lon == 0.0:
            return None

        ids_raw = props.get("ids", ",")
        event_id = "usgs-" + ids_raw.strip(",").split(",")[0]

        time_ms = props.get("time", 0)
        timestamp = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)

        return EarthquakeEvent(
            event_id=event_id,
            magnitude=float(magnitude),
            depth_km=depth_km,
            latitude=lat,
            longitude=lon,
            region=props.get("place", "Unknown"),
            timestamp=timestamp,
            source="usgs",
        )
    except Exception as e:
        logger.warning("[USGS] イベントパースエラー: %s", e)
        return None


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    """USGS API から日本周辺の最新地震リストを取得する。"""
    if not settings.usgs_enabled:
        return []

    min_lat, max_lat, min_lon, max_lon = settings.usgs_japan_bbox
    params = {
        "format": "geojson",
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
            resp = await client.get(settings.usgs_api_url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("[USGS] API エラー: %s", e)
        return []

    features = data.get("features", [])
    return [e for f in features if (e := _parse_feature(f))]
