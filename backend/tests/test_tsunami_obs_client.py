import pytest
from unittest.mock import patch
from app.infrastructure.tsunami_obs_client import fetch_recent_events, _parse_tsunami_feed

SAMPLE = """<feed><entry>
<title>津波警報・注意報</title>
<id>https://example.com/tsunami/001</id>
<updated>2026-03-25T10:00:00Z</updated>
</entry><entry>
<title>地震情報</title>
<id>https://example.com/eq/002</id>
<updated>2026-03-25T09:00:00Z</updated>
</entry></feed>"""

def test_parse_tsunami():
    events = _parse_tsunami_feed(SAMPLE)
    assert len(events) == 1  # 津波のみ
    assert events[0].source == "tsunami_obs"

def test_parse_empty():
    assert _parse_tsunami_feed("<feed></feed>") == []

@pytest.mark.asyncio
async def test_disabled(db_engine):
    with patch("app.infrastructure.tsunami_obs_client.settings") as mock:
        mock.tsunami_obs_enabled = False
        result = await fetch_recent_events()
    assert result == []
