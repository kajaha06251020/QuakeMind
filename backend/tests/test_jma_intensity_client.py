import pytest
from unittest.mock import patch
from app.infrastructure.jma_intensity_client import fetch_recent_events, _parse_intensity_feed

SAMPLE_FEED = """<?xml version="1.0"?>
<feed><entry>
<title>震度速報</title>
<id>https://example.com/entry/12345</id>
<updated>2026-03-25T10:00:00Z</updated>
</entry></feed>"""

def test_parse_intensity():
    events = _parse_intensity_feed(SAMPLE_FEED)
    assert len(events) == 1
    assert events[0].source == "jma_intensity"

def test_parse_empty():
    events = _parse_intensity_feed("<feed></feed>")
    assert events == []

@pytest.mark.asyncio
async def test_disabled(db_engine):
    with patch("app.infrastructure.jma_intensity_client.settings") as mock:
        mock.jma_intensity_enabled = False
        result = await fetch_recent_events()
    assert result == []
