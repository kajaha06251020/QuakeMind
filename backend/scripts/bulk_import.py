"""USGS/IRIS 過去データの一括インポートスクリプト。

使い方: cd backend && .venv/Scripts/python -m scripts.bulk_import --source usgs --years 5
"""
import asyncio
import argparse
import logging
from datetime import datetime, timedelta, timezone

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_FDSN_URLS = {
    "usgs": "https://earthquake.usgs.gov/fdsnws/event/1/query",
    "iris": "https://service.iris.edu/fdsnws/event/1/query",
    "emsc": "https://www.seismicportal.eu/fdsnws/event/1/query",
}

_JAPAN_BBOX = {"minlatitude": 24, "maxlatitude": 46, "minlongitude": 122, "maxlongitude": 154}


async def fetch_period(source: str, start: datetime, end: datetime, min_mag: float = 2.0) -> list[dict]:
    """指定期間のイベントを FDSN text 形式で取得する。"""
    url = _FDSN_URLS.get(source)
    if not url:
        logger.error("Unknown source: %s", source)
        return []

    params = {
        "format": "text",
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": min_mag,
        **_JAPAN_BBOX,
        "orderby": "time",
        "limit": 20000,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return _parse_fdsn(resp.text, source)
    except Exception as e:
        logger.error("[BulkImport] %s %s-%s エラー: %s", source, start.date(), end.date(), e)
        return []


def _parse_fdsn(text: str, source: str) -> list[dict]:
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("#") or line.startswith("EventID"):
            continue
        parts = line.split("|")
        if len(parts) < 11:
            continue
        try:
            events.append({
                "event_id": f"{source}-{parts[0].strip()}",
                "source": source,
                "magnitude": float(parts[10].strip()) if parts[10].strip() else 0,
                "depth_km": float(parts[4].strip()) if parts[4].strip() else 0,
                "latitude": float(parts[2].strip()),
                "longitude": float(parts[3].strip()),
                "region": parts[12].strip() if len(parts) > 12 else "Unknown",
                "timestamp": parts[1].strip(),
            })
        except Exception:
            continue
    return events


async def run_import(source: str, years: int, min_mag: float):
    """年単位で分割してインポートする。"""
    # DB初期化
    from app.infrastructure.database import init_db, get_session_factory, override_engine
    from app.infrastructure.database import get_engine
    from app.infrastructure.models_db import EarthquakeEventDB
    from sqlalchemy import select
    import uuid

    await init_db()
    factory = get_session_factory()

    end = datetime.now(timezone.utc)
    total_imported = 0

    for y in range(years):
        period_end = end - timedelta(days=365 * y)
        period_start = end - timedelta(days=365 * (y + 1))
        logger.info("[BulkImport] %s: %s → %s", source, period_start.date(), period_end.date())

        events = await fetch_period(source, period_start, period_end, min_mag)
        logger.info("[BulkImport] %d 件取得", len(events))

        # DB に保存（重複スキップ）
        saved = 0
        async with factory() as session:
            for ev in events:
                existing = await session.execute(
                    select(EarthquakeEventDB.event_id).where(EarthquakeEventDB.event_id == ev["event_id"])
                )
                if existing.scalar_one_or_none() is not None:
                    continue
                try:
                    ts = datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)
                session.add(EarthquakeEventDB(
                    id=uuid.uuid4(),
                    event_id=ev["event_id"],
                    source=ev["source"],
                    magnitude=ev["magnitude"],
                    depth_km=ev["depth_km"],
                    latitude=ev["latitude"],
                    longitude=ev["longitude"],
                    region=ev["region"],
                    occurred_at=ts,
                    fetched_at=datetime.now(timezone.utc),
                ))
                saved += 1
            await session.commit()

        logger.info("[BulkImport] %d 件保存（重複除外）", saved)
        total_imported += saved

    logger.info("[BulkImport] 完了: 合計 %d 件インポート", total_imported)


def main():
    parser = argparse.ArgumentParser(description="地震データ一括インポート")
    parser.add_argument("--source", choices=list(_FDSN_URLS.keys()), default="usgs")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--min-mag", type=float, default=2.0)
    args = parser.parse_args()

    asyncio.run(run_import(args.source, args.years, args.min_mag))


if __name__ == "__main__":
    main()
