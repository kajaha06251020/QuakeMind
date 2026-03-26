"""FastAPI アプリケーション。"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, field_validator

from app.config import settings, configure_langsmith
from app.infrastructure import db, jma_client
from app.infrastructure.multi_source import fetch_all_sources
from app.interfaces.analysis_router import router as analysis_router
from app.usecases.pipeline import graph

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_data_stale = False
_last_updated: Optional[datetime] = None


async def require_api_key(key: str = Security(_api_key_header)) -> str:
    if not key or key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


async def _process_event(event) -> None:
    # earthquake_events に保存（WS モードでも漏れないようここで保存）
    try:
        from app.usecases.event_store import save_events
        await save_events([event])
    except Exception as e:
        logger.warning("[Monitor] イベント保存失敗: %s", e)

    initial_state = {
        "event_id": event.event_id,
        "magnitude": event.magnitude,
        "depth_km": event.depth_km,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "region": event.region,
        "timestamp": event.timestamp.isoformat(),
        "error": "",
        "is_fallback": False,
    }
    try:
        await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("[Monitor] パイプラインエラー %s: %s", event.event_id, e)


async def monitor_loop() -> None:
    global _data_stale, _last_updated
    logger.info("Monitor ループ開始（間隔: %ds）", settings.poll_interval_seconds)
    while True:
        try:
            events = await fetch_all_sources(limit=20)
            _last_updated = datetime.now(timezone.utc)
            _data_stale = len(events) == 0

            for event in events:
                if not await db.is_event_seen(event.event_id):
                    await db.mark_event_seen(event.event_id)
                    if event.magnitude >= settings.magnitude_threshold:
                        await _process_event(event)

        except asyncio.CancelledError:
            logger.info("Monitor ループ停止")
            raise
        except Exception as e:
            logger.error("[Monitor] ループエラー: %s", e)

        await asyncio.sleep(settings.poll_interval_seconds)


async def ws_monitor_loop() -> None:
    global _data_stale, _last_updated
    logger.info("WebSocket モニターループ開始")
    async for event in jma_client.stream_events():
        _last_updated = datetime.now(timezone.utc)
        _data_stale = False
        try:
            if not await db.is_event_seen(event.event_id):
                await db.mark_event_seen(event.event_id)
                if event.magnitude >= settings.magnitude_threshold:
                    await _process_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("[WSMonitor] イベント処理エラー %s: %s", event.event_id, e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_langsmith()
    await db.init_db()
    from app.services.health import set_started_at
    set_started_at()
    if settings.p2p_ws_url:
        task = asyncio.create_task(ws_monitor_loop())
    else:
        task = asyncio.create_task(monitor_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="QuakeMind API",
    description="自律型防災 AGI — Phase 1 + Phase 2 研究ツール",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)


@app.get("/status")
async def get_status():
    status = await db.get_db_status()
    latest = status.get("latest")
    latest_risk = None
    if latest and latest.get("risk_json"):
        try:
            latest_risk = json.loads(latest["risk_json"])
        except Exception:
            pass
    return {
        "last_updated": _last_updated.isoformat() if _last_updated else None,
        "data_stale": _data_stale,
        "latest_risk_score": latest_risk,
        "total_alerts": status.get("total_alerts", 0),
    }


@app.get("/alert/latest")
async def get_latest_alert():
    row = await db.get_latest_alert()
    if not row:
        raise HTTPException(status_code=404, detail="アラートがまだありません")
    return {
        "event_id": row["event_id"],
        "severity": row["severity"],
        "ja_text": row["ja_text"],
        "en_text": row["en_text"],
        "is_fallback": bool(row["is_fallback"]),
        "timestamp": row["timestamp"],
    }


@app.get("/locations")
async def get_alert_locations(limit: int = Query(default=50, ge=1, le=200)):
    """マップ表示用の震源地位置情報リスト。"""
    locations = await db.get_alert_locations(limit=limit)
    return {"locations": locations}


@app.get("/alerts")
async def get_alerts(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    alerts, total = await db.get_alerts(limit=limit, offset=offset)
    return {
        "alerts": [
            {
                "event_id": row["event_id"],
                "severity": row["severity"],
                "ja_text": row["ja_text"],
                "en_text": row["en_text"],
                "is_fallback": bool(row["is_fallback"]),
                "timestamp": row["timestamp"],
            }
            for row in alerts
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/events")
async def get_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    min_magnitude: Optional[float] = None,
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    events, total = await db.get_events(
        limit=limit, offset=offset,
        min_magnitude=min_magnitude, region=region,
        start=start_dt, end=end_dt,
    )
    return {"events": events, "total": total, "limit": limit, "offset": offset}


@app.get("/events/stream")
async def stream_events(request: Request):
    """SSE: 新アラートが発生するたびにデータをプッシュする。"""
    async def generator():
        last_event_id: str | None = None
        # 最初にheartbeatを送信
        yield ": heartbeat\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                row = await db.get_latest_alert()
                if row and row["event_id"] != last_event_id:
                    last_event_id = row["event_id"]
                    payload = json.dumps(
                        {
                            "event_id": row["event_id"],
                            "severity": row["severity"],
                            "ja_text": row["ja_text"],
                            "timestamp": str(row["timestamp"]),
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
            except Exception as e:
                logger.error("[SSE] ジェネレーターエラー: %s", e)
                yield "event: error\ndata: internal error\n\n"
                break
            await asyncio.sleep(3)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class TriggerRequest(BaseModel):
    test_mode: bool = False
    magnitude_override: Optional[float] = None


@app.post("/trigger", dependencies=[Depends(require_api_key)])
async def trigger_monitor(body: TriggerRequest):
    if body.magnitude_override is not None and not (0.0 <= body.magnitude_override <= 10.0):
        raise HTTPException(status_code=422, detail="magnitude_override は 0.0〜10.0 で指定してください")
    trigger_id = f"manual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    asyncio.create_task(_one_shot_poll(body.magnitude_override))
    return {"status": "triggered", "trigger_id": trigger_id}


async def _one_shot_poll(magnitude_override: Optional[float]) -> None:
    events = await fetch_all_sources(limit=5)
    for event in events:
        if magnitude_override is not None:
            event = event.model_copy(update={"magnitude": magnitude_override})
        if not await db.is_event_seen(event.event_id):
            await _process_event(event)
            await db.mark_event_seen(event.event_id)


class SettingsUpdate(BaseModel):
    min_severity: Optional[str] = None
    region_filters: Optional[list[str]] = None
    notification_channels: Optional[list[dict]] = None

    @field_validator("min_severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        if v is not None and v not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError("severity は LOW/MEDIUM/HIGH/CRITICAL のいずれかです")
        return v


@app.get("/settings")
async def get_settings():
    return await db.get_user_settings()


@app.put("/settings")
async def update_settings(body: SettingsUpdate):
    return await db.update_user_settings(
        min_severity=body.min_severity,
        region_filters=body.region_filters,
        notification_channels=body.notification_channels,
    )


@app.get("/health")
async def health_check():
    from app.services.health import check_health
    return await check_health()
