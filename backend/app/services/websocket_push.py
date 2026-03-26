"""WebSocketリアルタイムプッシュ。新しい発見を即座にクライアントに通知。"""
import asyncio, logging, json
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_connections: list = []
_message_log: list[dict] = []

async def broadcast(event_type: str, data: dict) -> int:
    """全接続クライアントにメッセージをプッシュする。"""
    message = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, default=str)
    _message_log.append({"type": event_type, "timestamp": datetime.now(timezone.utc).isoformat()})
    sent = 0
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(message)
            sent += 1
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)
    return sent

def register_connection(ws) -> None:
    _connections.append(ws)

def remove_connection(ws) -> None:
    if ws in _connections: _connections.remove(ws)

def get_ws_status() -> dict:
    return {"active_connections": len(_connections), "total_messages_sent": len(_message_log), "recent_messages": _message_log[-10:]}
