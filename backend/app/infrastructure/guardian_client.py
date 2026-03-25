"""NASA GUARDIAN TEC 異常シグナルクライアント。

電離層 TEC 異常を地震前兆シグナルとして取得する。
guardian_api_url は .env で設定する。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class TecAnomaly(BaseModel):
    """電離層 TEC 異常観測データ。"""
    region: str
    anomaly_score: float   # 0.0 (正常) 〜 1.0 (強い異常)
    latitude: float
    longitude: float
    observed_at: datetime
    source: str = "guardian"


def _parse_anomaly(raw: dict) -> Optional[TecAnomaly]:
    try:
        observed_str = raw.get("observed_at", "")
        try:
            observed_at = datetime.fromisoformat(observed_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            observed_at = datetime.now(timezone.utc)

        return TecAnomaly(
            region=raw.get("region", "Unknown"),
            anomaly_score=float(raw.get("anomaly_score", 0.0)),
            latitude=float(raw.get("latitude", 0.0)),
            longitude=float(raw.get("longitude", 0.0)),
            observed_at=observed_at,
        )
    except Exception as e:
        logger.warning("[GUARDIAN] パースエラー: %s", e)
        return None


async def fetch_tec_anomalies() -> list[TecAnomaly]:
    """GUARDIAN API から TEC 異常データを取得する。
    guardian_enabled=False または guardian_api_url 未設定の場合は空リストを返す。
    """
    if not settings.guardian_enabled or not settings.guardian_api_url:
        return []

    try:
        async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
            resp = await client.get(settings.guardian_api_url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("[GUARDIAN] API エラー: %s", e)
        return []

    anomalies = data.get("anomalies", [])
    return [a for raw in anomalies if (a := _parse_anomaly(raw))]
