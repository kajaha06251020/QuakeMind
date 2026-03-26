"""Test EMSC client."""
import pytest
from app.infrastructure.emsc_client import fetch_recent_events, _parse_fdsn_text


SAMPLE_FDSN_TEXT = """#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName
12345|2026-03-25T10:00:00Z|35.5|139.5|10.0|XXX|XXX|XXX|XXX|mb|5.2|XXX|Near Tokyo
67890|2026-03-25T09:00:00Z|34.0|135.0|20.0|XXX|XXX|XXX|XXX|ml|4.1|XXX|Near Osaka
"""


def test_parse_fdsn_text():
    events = _parse_fdsn_text(SAMPLE_FDSN_TEXT)
    assert len(events) == 2
    assert events[0].magnitude == 5.2
    assert events[0].source == "emsc"


def test_parse_fdsn_empty():
    events = _parse_fdsn_text("#header\n")
    assert events == []


@pytest.mark.asyncio
async def test_fetch_disabled(db_engine):
    # Disabled by patching settings
    from unittest.mock import patch
    with patch("app.infrastructure.emsc_client.settings") as mock:
        mock.emsc_enabled = False
        result = await fetch_recent_events()
    assert result == []
