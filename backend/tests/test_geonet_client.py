import pytest
from unittest.mock import patch
from app.infrastructure.geonet_client import fetch_recent_events

@pytest.mark.asyncio
async def test_geonet_disabled(db_engine):
    with patch("app.infrastructure.geonet_client.settings") as mock:
        mock.geonet_enabled = False
        result = await fetch_recent_events()
    assert result == []
