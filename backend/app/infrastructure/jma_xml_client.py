"""気象庁防災情報 XML 電文クライアント。

Atom Feed から地震情報 XML (VXSE53) を取得・パースする。
座標フォーマット: ISO 6709 (+緯度+経度-深さm/)
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from lxml import etree

from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)

_NS = {
    "jmx": "http://xml.kishou.go.jp/jmaxml1/",
    "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis/",
    "atom": "http://www.w3.org/2005/Atom",
}

# ISO 6709 座標文字列のパターン例: "+35.6+139.7-20000/"
_ISO6709_RE = re.compile(r"([+-]\d+\.?\d*)([+-]\d+\.?\d*)([+-]\d+\.?\d*)/")


def _parse_iso6709(coord_str: str) -> Optional[tuple[float, float, float]]:
    """ISO 6709 形式の座標文字列を (緯度, 経度, 深さkm) にパースする。
    深さは メートル単位で格納されているため 1000 で割る。
    """
    if not coord_str:
        return None
    m = _ISO6709_RE.search(coord_str.strip())
    if not m:
        return None
    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        depth_m = float(m.group(3))
        depth_km = abs(depth_m) / 1000.0
        return lat, lon, depth_km
    except ValueError:
        return None


def _parse_jma_earthquake_xml(xml_text: str, event_id: str) -> Optional[EarthquakeEvent]:
    """気象庁 XML 電文（VXSE53 形式）から EarthquakeEvent を生成する。"""
    try:
        root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
        eq = root.find(".//jmx:Body/jmx:Earthquake", _NS)
        if eq is None:
            eq = root.find(".//{http://xml.kishou.go.jp/jmaxml1/}Earthquake")
        if eq is None:
            return None

        mag_el = eq.find(".//{http://xml.kishou.go.jp/jmaxml1/}Magnitude")
        if mag_el is None or mag_el.text is None:
            return None
        magnitude = float(mag_el.text.strip())
        if magnitude < 0:
            return None

        coord_el = eq.find(".//{http://xml.kishou.go.jp/jmaxml1/elementBasis/}Coordinate")
        if coord_el is None or coord_el.text is None:
            return None
        parsed = _parse_iso6709(coord_el.text)
        if parsed is None:
            return None
        lat, lon, depth_km = parsed

        name_el = eq.find(".//{http://xml.kishou.go.jp/jmaxml1/}Name")
        region = name_el.text.strip() if name_el is not None and name_el.text else "不明"

        time_el = eq.find(".//{http://xml.kishou.go.jp/jmaxml1/}OriginTime")
        if time_el is not None and time_el.text:
            try:
                timestamp = datetime.fromisoformat(time_el.text.strip())
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        return EarthquakeEvent(
            event_id=event_id,
            magnitude=magnitude,
            depth_km=depth_km,
            latitude=lat,
            longitude=lon,
            region=region,
            timestamp=timestamp,
            source="jma",
        )
    except Exception as e:
        logger.warning("[JMA XML] パースエラー event_id=%s: %s", event_id, e)
        return None


async def fetch_recent_events(limit: int = 20) -> list[EarthquakeEvent]:
    """Atom Feed から最新の地震情報 XML を取得してパースする。"""
    if not settings.jma_xml_enabled:
        return []

    async with httpx.AsyncClient(timeout=settings.jma_timeout) as client:
        # Atom Feed 取得
        try:
            resp = await client.get(settings.jma_xml_feed_url)
            resp.raise_for_status()
            feed_root = etree.fromstring(resp.content)
        except Exception as e:
            logger.error("[JMA XML] Atom Feed 取得エラー: %s", e)
            return []

        # 震源情報エントリを収集
        entries = feed_root.findall("{http://www.w3.org/2005/Atom}entry")
        targets = []
        for entry in entries[:limit]:
            id_el = entry.find("{http://www.w3.org/2005/Atom}id")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            if id_el is None or link_el is None:
                continue
            xml_url = link_el.get("href", "")
            if not xml_url:
                continue
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            if title_el is None or "震源" not in (title_el.text or ""):
                continue
            event_id = "jma-" + (id_el.text or "").strip().split("/")[-1]
            targets.append((event_id, xml_url))

        # 個別 XML を並列取得
        async def _fetch_one(event_id: str, xml_url: str) -> EarthquakeEvent | None:
            try:
                xml_resp = await client.get(xml_url)
                xml_resp.raise_for_status()
                event = _parse_jma_earthquake_xml(xml_resp.text, event_id)
                if event and event.magnitude >= settings.magnitude_threshold:
                    return event
            except Exception as e:
                logger.warning("[JMA XML] XML 取得エラー %s: %s", xml_url, e)
            return None

        results = await asyncio.gather(*(_fetch_one(eid, url) for eid, url in targets))
    return [e for e in results if e is not None]
