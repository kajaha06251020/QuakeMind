"""JMA XML クライアントのユニットテスト。"""
import pytest

from app.infrastructure.jma_xml_client import _parse_iso6709, _parse_jma_earthquake_xml


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Report xmlns="http://xml.kishou.go.jp/jmaxml1/"
        xmlns:jmx_eb="http://xml.kishou.go.jp/jmaxml1/elementBasis/">
  <Control>
    <Title>震源・震度情報</Title>
    <DateTime>2026-03-25T12:00:00Z</DateTime>
    <EventID>20260325120000</EventID>
  </Control>
  <Body>
    <Earthquake>
      <OriginTime>2026-03-25T12:00:00+09:00</OriginTime>
      <Magnitude description="M5.5">5.5</Magnitude>
      <Hypocenter>
        <Area>
          <Name>東京湾</Name>
          <jmx_eb:Coordinate description="北緯35.6度 東経139.7度 深さ 20km">
            +35.6+139.7-20000/
          </jmx_eb:Coordinate>
        </Area>
      </Hypocenter>
    </Earthquake>
  </Body>
</Report>"""


def test_parse_iso6709_basic():
    """基本的な ISO 6709 座標文字列をパースできる。"""
    lat, lon, depth_km = _parse_iso6709("+35.6+139.7-20000/")
    assert lat == pytest.approx(35.6)
    assert lon == pytest.approx(139.7)
    assert depth_km == pytest.approx(20.0)


def test_parse_iso6709_negative_lat():
    """南緯（負の緯度）もパースできる。"""
    lat, lon, depth_km = _parse_iso6709("-10.0+140.0-15000/")
    assert lat == pytest.approx(-10.0)


def test_parse_iso6709_returns_none_on_invalid():
    """無効な文字列は None を返す。"""
    assert _parse_iso6709("invalid") is None
    assert _parse_iso6709("") is None


def test_parse_jma_xml_returns_event():
    """サンプル XML から EarthquakeEvent をパースできる。"""
    from app.domain.models import EarthquakeEvent
    event = _parse_jma_earthquake_xml(SAMPLE_XML, event_id="jma-20260325")
    assert event is not None
    assert isinstance(event, EarthquakeEvent)
    assert event.magnitude == 5.5
    assert event.region == "東京湾"
    assert event.source == "jma"


def test_parse_jma_xml_invalid_returns_none():
    """不正な XML は None を返す。"""
    event = _parse_jma_earthquake_xml("<invalid>", event_id="jma-bad")
    assert event is None


@pytest.mark.asyncio
async def test_fetch_disabled_returns_empty():
    """jma_xml_enabled=False のとき HTTP を呼ばずに空リストを返す。"""
    from app.infrastructure.jma_xml_client import fetch_recent_events
    from unittest.mock import patch

    with patch("app.infrastructure.jma_xml_client.settings") as mock_settings:
        mock_settings.jma_xml_enabled = False
        events = await fetch_recent_events()

    assert events == []
