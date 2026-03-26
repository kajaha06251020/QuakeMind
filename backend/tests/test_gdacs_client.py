import pytest
from unittest.mock import patch
from app.infrastructure.gdacs_client import fetch_recent_events, _parse_gdacs_rss

SAMPLE_RSS = """<?xml version="1.0"?>
<rss><channel>
<item>
<title>M 5.3 - Japan</title>
<geo:lat>35.5</geo:lat>
<geo:long>139.5</geo:long>
<pubDate>Tue, 25 Mar 2026 10:00:00 GMT</pubDate>
<guid>https://gdacs.org/report.aspx?eventid=12345</guid>
<description>Earthquake near Tokyo</description>
</item>
</channel></rss>"""


def test_parse_gdacs_rss():
    events = _parse_gdacs_rss(SAMPLE_RSS)
    assert len(events) == 1
    assert events[0].magnitude == 5.3
    assert events[0].source == "gdacs"


def test_parse_gdacs_empty():
    events = _parse_gdacs_rss("<rss><channel></channel></rss>")
    assert events == []


@pytest.mark.asyncio
async def test_gdacs_disabled(db_engine):
    with patch("app.infrastructure.gdacs_client.settings") as mock:
        mock.gdacs_enabled = False
        result = await fetch_recent_events()
    assert result == []
