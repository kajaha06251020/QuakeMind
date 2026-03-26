"""データパイプライン監視。各ソースの取得状態をトラッキング。"""
import logging
from datetime import datetime, timezone, timedelta

from app.infrastructure.multi_source import get_source_status

logger = logging.getLogger(__name__)

# ソースごとの期待取得間隔（秒）
_EXPECTED_INTERVALS = {
    "p2p": 120,
    "usgs": 120,
    "jma_xml": 300,
    "emsc": 120,
    "iris": 120,
    "geonet": 120,
    "ingv": 120,
    "gdacs": 600,
    "jma_intensity": 300,
    "tsunami_obs": 300,
}


def check_pipeline_health() -> dict:
    """全データソースのパイプライン状態を評価する。"""
    raw = get_source_status()
    now = datetime.now(timezone.utc)

    sources = {}
    alerts = []

    for name, expected_sec in _EXPECTED_INTERVALS.items():
        status = raw.get(name)
        if status is None:
            sources[name] = {"status": "no_data", "last_fetch_at": None, "delay_seconds": None}
            continue

        last_fetch = status.get("last_fetch_at")
        last_error = status.get("last_error")

        delay_sec = None
        if last_fetch:
            try:
                fetch_time = datetime.fromisoformat(last_fetch)
                delay_sec = (now - fetch_time).total_seconds()
            except Exception:
                pass

        is_delayed = delay_sec is not None and delay_sec > expected_sec * 3
        is_errored = last_error is not None

        if is_delayed:
            status_str = "delayed"
            alerts.append(f"{name}: {delay_sec:.0f}秒遅延（期待: {expected_sec}秒以内）")
        elif is_errored:
            status_str = "error"
            alerts.append(f"{name}: エラー - {last_error}")
        else:
            status_str = "healthy"

        sources[name] = {
            "status": status_str,
            "last_fetch_at": last_fetch,
            "last_error": last_error,
            "delay_seconds": round(delay_sec, 1) if delay_sec else None,
            "expected_interval_seconds": expected_sec,
        }

    healthy_count = sum(1 for s in sources.values() if s["status"] == "healthy")
    total = len(sources)

    return {
        "overall": "healthy" if not alerts else "degraded",
        "healthy_sources": healthy_count,
        "total_sources": total,
        "alerts": alerts,
        "sources": sources,
    }
