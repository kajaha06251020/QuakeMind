"""SQLite 永続化レイヤー。"""
import logging
from datetime import datetime
from typing import Optional

import aiosqlite

from app.config import settings
from app.domain.models import AlertMessage, RiskScore, EvacuationRoute

logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_events (
                event_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                event_id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                ja_text TEXT NOT NULL,
                en_text TEXT NOT NULL,
                is_fallback INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                risk_json TEXT,
                route_json TEXT
            )
        """)
        await db.commit()
    logger.info("DB initialized: %s", settings.db_path)


async def is_event_seen(event_id: str) -> bool:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT 1 FROM seen_events WHERE event_id = ?", (event_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def mark_event_seen(event_id: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO seen_events (event_id, created_at) VALUES (?, ?)",
            (event_id, datetime.utcnow().isoformat()),
        )
        await db.execute(f"""
            DELETE FROM seen_events WHERE event_id NOT IN (
                SELECT event_id FROM seen_events
                ORDER BY created_at DESC LIMIT {settings.max_seen_ids}
            )
        """)
        await db.commit()


async def save_alert(
    alert: AlertMessage,
    risk: Optional[RiskScore] = None,
    route: Optional[EvacuationRoute] = None,
) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO alerts
               (event_id, severity, ja_text, en_text, is_fallback, timestamp, risk_json, route_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert.event_id,
                alert.severity,
                alert.ja_text,
                alert.en_text,
                int(alert.is_fallback),
                alert.timestamp.isoformat(),
                risk.model_dump_json() if risk else None,
                route.model_dump_json() if route else None,
            ),
        )
        await db.execute(f"""
            DELETE FROM alerts WHERE event_id NOT IN (
                SELECT event_id FROM alerts
                ORDER BY timestamp DESC LIMIT {settings.max_events}
            )
        """)
        await db.commit()


async def get_latest_alert() -> Optional[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_db_status() -> dict:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM alerts") as cursor:
            total = (await cursor.fetchone())[0]
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
    return {"total_alerts": total, "latest": dict(row) if row else None}


async def get_alert_locations(limit: int = 50) -> list[dict]:
    """最新N件のアラートの震源地位置情報を取得（マップ表示用）。"""
    import json as _json
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT event_id, severity, timestamp, route_json FROM alerts ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()

    result = []
    for row in rows:
        if not row["route_json"]:
            continue
        try:
            route = _json.loads(row["route_json"])
            lat = route.get("latitude")
            lon = route.get("longitude")
            if lat is None or lon is None:
                continue
            result.append({
                "event_id": row["event_id"],
                "severity": row["severity"],
                "timestamp": str(row["timestamp"]),
                "latitude": lat,
                "longitude": lon,
                "danger_radius_km": route.get("danger_radius_km"),
            })
        except Exception:
            continue
    return result


async def get_alerts(limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    """アラート履歴を新しい順で取得。(alerts, total) を返す。"""
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM alerts") as cursor:
            total = (await cursor.fetchone())[0]
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows], total
