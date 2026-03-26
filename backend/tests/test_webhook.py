"""Webhook ディスパッチャーのユニットテスト。"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.domain.models import AlertMessage


def _make_alert(severity="HIGH", is_fallback=False) -> AlertMessage:
    return AlertMessage(
        event_id="test-001",
        severity=severity,
        ja_text="東京湾でM5.5の地震が発生しました",
        en_text="Earthquake M5.5 near Tokyo Bay",
        is_fallback=is_fallback,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_dispatch_sends_post_to_all_urls():
    """設定された全 URL に POST を送信する。"""
    from app.services.webhook import dispatch_webhooks

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    alert = _make_alert()
    with patch("app.services.webhook.httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.webhook.settings") as mock_settings:
            mock_settings.webhook_urls = ["https://hooks.example.com/a", "https://hooks.example.com/b"]
            mock_settings.webhook_timeout = 5.0
            await dispatch_webhooks(alert)

    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_dispatch_no_urls_is_noop():
    """webhook_urls が空のとき、POST は呼ばれない。"""
    from app.services.webhook import dispatch_webhooks

    with patch("app.services.webhook.settings") as mock_settings:
        mock_settings.webhook_urls = []
        mock_settings.webhook_timeout = 5.0
        await dispatch_webhooks(_make_alert())
    # 例外が発生しないことを確認（暗黙のアサーション）


@pytest.mark.asyncio
async def test_dispatch_failure_does_not_raise():
    """POST 失敗時も例外を送出しない（エラーログのみ）。"""
    import httpx
    from app.services.webhook import dispatch_webhooks

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    alert = _make_alert()
    with patch("app.services.webhook.httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.webhook.settings") as mock_settings:
            mock_settings.webhook_urls = ["https://hooks.example.com/fail"]
            mock_settings.webhook_timeout = 5.0
            await dispatch_webhooks(alert)
    # 例外が発生しないことを確認（暗黙のアサーション）
