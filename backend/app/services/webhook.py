"""外部 Webhook への通知ディスパッチャー。"""
import logging

import httpx

from app.config import settings
from app.domain.models import AlertMessage

logger = logging.getLogger(__name__)


async def dispatch_webhooks(alert: AlertMessage) -> None:
    """設定された全 webhook_urls に AlertMessage を POST する。
    失敗しても例外は送出しない（エラーはログのみ）。
    """
    if not settings.webhook_urls:
        return

    payload = {
        "event_id": alert.event_id,
        "severity": alert.severity,
        "ja_text": alert.ja_text,
        "en_text": alert.en_text,
        "timestamp": alert.timestamp.isoformat(),
        "is_fallback": alert.is_fallback,
    }

    async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
        for url in settings.webhook_urls:
            try:
                resp = await client.post(url, json=payload)
                logger.info("[Webhook] POST %s → %d", url, resp.status_code)
            except Exception as e:
                logger.error("[Webhook] POST 失敗 %s: %s", url, e)
