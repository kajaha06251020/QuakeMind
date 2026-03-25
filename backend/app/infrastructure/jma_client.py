"""P2P地震情報 API クライアント。"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
import websockets

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


async def stream_events() -> AsyncGenerator[EarthquakeEvent, None]:
    """P2P WebSocket から地震イベントをリアルタイムでストリーミング受信する。
    接続断時は settings.p2p_ws_reconnect_delay 秒後に自動再接続する。
    """
    while True:
        try:
            conn = websockets.connect(settings.p2p_ws_url)
            if asyncio.iscoroutine(conn):
                # テストモック（async side_effect）または将来の await-only API 向け
                ws = await conn
                async for raw_msg in ws:
                    try:
                        raw = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        logger.warning("[WS] JSON デコード失敗")
                        continue
                    if raw.get("code") != 551:
                        continue
                    event = _parse_p2p_event(raw)
                    if event:
                        yield event
            else:
                async with conn as ws:
                    logger.info("[WS] P2P WebSocket 接続: %s", settings.p2p_ws_url)
                    async for raw_msg in ws:
                        try:
                            raw = json.loads(raw_msg)
                        except json.JSONDecodeError:
                            logger.warning("[WS] JSON デコード失敗")
                            continue
                        if raw.get("code") != 551:
                            continue
                        event = _parse_p2p_event(raw)
                        if event:
                            yield event
        except asyncio.CancelledError:
            logger.info("[WS] WebSocket モニター停止")
            raise
        except Exception as e:
            logger.error("[WS] 接続エラー: %s — %ds後再接続", e, settings.p2p_ws_reconnect_delay)
            await asyncio.sleep(settings.p2p_ws_reconnect_delay)
