import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app.usecases.data_quality import score_data_sources

def test_score_healthy():
    now = datetime.now(timezone.utc).isoformat()
    with patch("app.usecases.data_quality.get_source_status", return_value={
        "p2p": {"last_fetch_at": now, "last_error": None},
        "usgs": {"last_fetch_at": now, "last_error": None},
    }):
        result = score_data_sources()
    assert result["overall_score"] >= 80
    assert result["sources"]["p2p"]["status"] == "healthy"

def test_score_with_error():
    now = datetime.now(timezone.utc).isoformat()
    with patch("app.usecases.data_quality.get_source_status", return_value={
        "p2p": {"last_fetch_at": now, "last_error": "timeout"},
    }):
        result = score_data_sources()
    assert result["sources"]["p2p"]["score"] <= 50

def test_score_empty():
    with patch("app.usecases.data_quality.get_source_status", return_value={}):
        result = score_data_sources()
    assert result["overall_score"] == 0
