"""FastAPI アプリケーション。"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from config import settings, configure_langsmith
from data import db, jma_client
from graph import graph

logger = logging.getLogger(__name__)

# ─── API キー認証（/trigger エンドポイント保護）────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str = Security(_api_key_header)) -> str:
    if not key or key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# ─── Monitor ループ ───────────────────────────────────────────────────────────

_data_stale = False
_last_updated: Optional[datetime] = None


async def _process_event(event) -> None:
    """1件の地震イベントを LangGraph パイプラインで処理する。"""
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
        logger.info("[Monitor] パイプライン完了: %s", event.event_id)
    except Exception as e:
        logger.error("[Monitor] パイプラインエラー %s: %s", event.event_id, e)


async def monitor_loop() -> None:
    """バックグラウンドポーリングループ。"""
    global _data_stale, _last_updated
    logger.info("Monitor ループ開始（間隔: %ds）", settings.poll_interval_seconds)

    while True:
        try:
            events = await jma_client.fetch_recent_events(limit=20)
            _last_updated = datetime.now(timezone.utc)

            if not events:
                _data_stale = True
                logger.warning("P2P API からイベントを取得できませんでした")
            else:
                _data_stale = False

            # 未処理イベントだけを処理
            new_events = []
            for event in events:
                if not await db.is_event_seen(event.event_id):
                    # 閾値チェック
                    if event.magnitude >= settings.magnitude_threshold:
                        new_events.append(event)
                    await db.mark_event_seen(event.event_id)

            if new_events:
                logger.info("[Monitor] 新規イベント %d 件を処理します", len(new_events))
                for event in new_events:
                    await _process_event(event)
            else:
                logger.debug("[Monitor] 新規対象イベントなし")

        except asyncio.CancelledError:
            logger.info("Monitor ループ停止")
            raise
        except Exception as e:
            logger.error("[Monitor] ループ内エラー: %s", e)

        await asyncio.sleep(settings.poll_interval_seconds)


# ─── FastAPI lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_langsmith()
    await db.init_db()
    task = asyncio.create_task(monitor_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Monitor ループを正常に停止しました")


# ─── FastAPI アプリ ────────────────────────────────────────────────────────────

app = FastAPI(
    title="QuakeMind API",
    description="自律型防災 AGI — 地震アラート生成システム (Phase 1)",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── エンドポイント ────────────────────────────────────────────────────────────

@app.get("/status", summary="最新リスクスコアとシステム状態を返す")
async def get_status():
    status = await db.get_status()
    latest = status.get("latest")

    import json
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


@app.get("/alert/latest", summary="最新の AlertMessage を返す")
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


class TriggerRequest(BaseModel):
    test_mode: bool = False
    magnitude_override: Optional[float] = None


@app.post(
    "/trigger",
    summary="Monitor を手動起動（開発・テスト用）",
    dependencies=[Depends(require_api_key)],
)
async def trigger_monitor(body: TriggerRequest):
    if body.magnitude_override is not None and not (0.0 <= body.magnitude_override <= 10.0):
        raise HTTPException(status_code=422, detail="magnitude_override は 0.0〜10.0 の範囲で指定してください")

    trigger_id = f"manual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    logger.info("[Trigger] 手動起動 id=%s test=%s", trigger_id, body.test_mode)

    # バックグラウンドで1回だけポーリングを実行
    asyncio.create_task(_one_shot_poll(body.magnitude_override))

    return {"status": "triggered", "trigger_id": trigger_id}


async def _one_shot_poll(magnitude_override: Optional[float]) -> None:
    events = await jma_client.fetch_recent_events(limit=5)
    for event in events:
        if magnitude_override:
            event = event.model_copy(update={"magnitude": magnitude_override})
        if not await db.is_event_seen(event.event_id):
            await _process_event(event)
            await db.mark_event_seen(event.event_id)
