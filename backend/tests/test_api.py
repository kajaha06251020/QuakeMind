"""APIエンドポイントのテスト。"""


def test_get_alerts_empty(client):
    """GET /alerts が正しいスキーマを返すこと。"""
    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["alerts"], list)


def test_get_alerts_limit_validation(client):
    """GET /alerts?limit=0 は 422 を返すこと。"""
    response = client.get("/alerts?limit=0")
    assert response.status_code == 422


def test_get_alerts_limit_max_validation(client):
    """GET /alerts?limit=101 は 422 を返すこと。"""
    response = client.get("/alerts?limit=101")
    assert response.status_code == 422


def test_get_status(client):
    """GET /status が動作すること。"""
    response = client.get("/status")
    assert response.status_code == 200


import pytest


@pytest.mark.anyio
async def test_sse_stream_headers():
    """GET /events/stream が text/event-stream を返すこと。"""
    import asyncio
    import anyio
    from app.interfaces.api import app as fastapi_app

    status_code = None
    content_type = None
    first_chunk = None

    async def run_request():
        nonlocal status_code, content_type, first_chunk

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "headers": [],
            "scheme": "http",
            "path": "/events/stream",
            "raw_path": b"/events/stream",
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        }

        body_queue: asyncio.Queue = asyncio.Queue()
        done_event = asyncio.Event()

        async def receive():
            await done_event.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code, content_type
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = dict(message.get("headers", []))
                content_type = headers.get(b"content-type", b"").decode()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    await body_queue.put(body)

        app_task = asyncio.create_task(fastapi_app(scope, receive, send))

        # 最初のチャンク（heartbeat）を待つ
        with anyio.move_on_after(5) as cancel_scope:
            first_chunk = (await body_queue.get()).decode()

        # disconnectを通知してgeneratorを停止させる
        done_event.set()
        app_task.cancel()
        try:
            await app_task
        except (asyncio.CancelledError, Exception):
            pass

    await run_request()

    assert status_code == 200
    assert "text/event-stream" in (content_type or "")
    assert first_chunk is not None
    assert "heartbeat" in first_chunk
