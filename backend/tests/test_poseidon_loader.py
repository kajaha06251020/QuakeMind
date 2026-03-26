"""POSEIDON Dataset ローダーのユニットテスト。"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.domain.models import EarthquakeEvent


MOCK_ROW = {
    "time": "2020-01-15T03:22:45.000Z",
    "latitude": 35.6,
    "longitude": 139.7,
    "depth": 20.0,
    "mag": 5.5,
    "place": "10 km N of Tokyo, Japan",
    "id": "us2020abc",
}

MOCK_ROW_INVALID = {
    "time": "2020-01-15T03:22:45.000Z",
    "latitude": 0.0,
    "longitude": 0.0,
    "depth": 20.0,
    "mag": -1.0,  # 無効
    "place": "Unknown",
    "id": "bad001",
}


def test_parse_poseidon_row_valid():
    """有効な行から EarthquakeEvent を生成できる。"""
    from app.services.poseidon_loader import _parse_poseidon_row
    event = _parse_poseidon_row(MOCK_ROW)
    assert event is not None
    assert isinstance(event, EarthquakeEvent)
    assert event.magnitude == 5.5
    assert event.source == "poseidon"
    assert event.event_id == "poseidon-us2020abc"


def test_parse_poseidon_row_invalid_returns_none():
    """無効データ（mag<0）は None を返す。"""
    from app.services.poseidon_loader import _parse_poseidon_row
    event = _parse_poseidon_row(MOCK_ROW_INVALID)
    assert event is None


def test_load_japan_sample_mocked():
    """データセットがモックされた状態で load_japan_sample が動作する。"""
    from app.services.poseidon_loader import load_japan_sample

    mock_dataset = MagicMock()
    mock_dataset.__iter__ = MagicMock(return_value=iter([MOCK_ROW, MOCK_ROW_INVALID]))

    with patch("app.services.poseidon_loader.load_dataset", return_value={"train": mock_dataset}):
        with patch("app.services.poseidon_loader.settings") as mock_settings:
            mock_settings.poseidon_enabled = True
            mock_settings.poseidon_dataset_name = "test/dataset"
            mock_settings.poseidon_sample_limit = 100
            mock_settings.usgs_japan_bbox = [24.0, 46.0, 122.0, 154.0]
            mock_settings.magnitude_threshold = 4.0
            events = load_japan_sample()

    assert len(events) == 1
    assert events[0].magnitude == 5.5


def test_load_japan_sample_disabled():
    """poseidon_enabled=False のとき空リストを返す。"""
    from app.services.poseidon_loader import load_japan_sample

    with patch("app.services.poseidon_loader.settings") as mock_settings:
        mock_settings.poseidon_enabled = False
        result = load_japan_sample()

    assert result == []
