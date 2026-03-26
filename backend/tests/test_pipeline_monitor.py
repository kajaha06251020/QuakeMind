import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app.services.pipeline_monitor import check_pipeline_health


def test_pipeline_healthy():
    now = datetime.now(timezone.utc).isoformat()
    with patch("app.services.pipeline_monitor.get_source_status", return_value={
        "p2p": {"last_fetch_at": now, "last_error": None},
        "usgs": {"last_fetch_at": now, "last_error": None},
    }):
        result = check_pipeline_health()
    assert result["healthy_sources"] >= 2
    assert len(result["alerts"]) == 0


def test_pipeline_with_error():
    now = datetime.now(timezone.utc).isoformat()
    with patch("app.services.pipeline_monitor.get_source_status", return_value={
        "p2p": {"last_fetch_at": now, "last_error": "timeout"},
    }):
        result = check_pipeline_health()
    assert result["overall"] == "degraded"
    assert len(result["alerts"]) > 0


def test_pipeline_empty():
    with patch("app.services.pipeline_monitor.get_source_status", return_value={}):
        result = check_pipeline_health()
    assert result["healthy_sources"] == 0
