"""インバウンドWebhook。外部システムからQuakeMindにデータを送り込む。"""
import logging
import uuid
from datetime import datetime, timezone

from app.domain.models import EarthquakeEvent
from app.usecases.event_store import save_events

logger = logging.getLogger(__name__)


async def process_inbound_event(payload: dict) -> dict:
    """外部システムからの地震イベントを処理する。"""
    required = ["magnitude", "latitude", "longitude"]
    missing = [f for f in required if f not in payload]
    if missing:
        return {"error": f"必須フィールドが不足: {missing}"}

    event = EarthquakeEvent(
        event_id=payload.get("event_id", f"inbound-{uuid.uuid4().hex[:12]}"),
        magnitude=float(payload["magnitude"]),
        depth_km=float(payload.get("depth_km", 0)),
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        region=payload.get("region", "Unknown"),
        timestamp=datetime.fromisoformat(payload["timestamp"]) if "timestamp" in payload else datetime.now(timezone.utc),
        source=payload.get("source", "inbound"),
    )

    saved = await save_events([event])
    return {
        "status": "accepted",
        "event_id": event.event_id,
        "saved": saved > 0,
    }
