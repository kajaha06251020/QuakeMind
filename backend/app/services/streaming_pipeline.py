"""ストリーミング分析パイプライン。イベント到着時に全分析を自動起動する。"""
import asyncio, logging
from datetime import datetime, timezone
from app.domain.models import EarthquakeEvent
logger = logging.getLogger(__name__)

_pipeline_hooks: list = []
_pipeline_log: list = []

def register_hook(name: str, func) -> None:
    _pipeline_hooks.append({"name": name, "func": func})

async def on_event_arrived(event: EarthquakeEvent) -> dict:
    """イベント到着時に全フックを実行する。"""
    results = {}
    for hook in _pipeline_hooks:
        try:
            result = await hook["func"](event) if asyncio.iscoroutinefunction(hook["func"]) else hook["func"](event)
            results[hook["name"]] = {"status": "ok", "result": str(result)[:200]}
        except Exception as e:
            results[hook["name"]] = {"status": "error", "error": str(e)}
    _pipeline_log.append({"event_id": event.event_id, "timestamp": datetime.now(timezone.utc).isoformat(), "hooks_executed": len(results), "results": results})
    return {"event_id": event.event_id, "hooks_executed": len(results), "results": results}

def get_pipeline_status() -> dict:
    return {"registered_hooks": [h["name"] for h in _pipeline_hooks], "n_hooks": len(_pipeline_hooks), "recent_executions": _pipeline_log[-10:]}
