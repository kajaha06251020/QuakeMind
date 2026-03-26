"""交通情報サービス。

JARTIC/Google Maps の実API は有料のため、参照URLと主要道路の震度別影響推定を提供。
"""
import logging

logger = logging.getLogger(__name__)

_JARTIC_URL = "https://www.jartic.or.jp/"
_NEXCO_URLS = {
    "east": "https://www.drivetraffic.jp/",
    "central": "https://c-nexco.co.jp/",
    "west": "https://www.w-nexco.co.jp/",
}


def get_traffic_info_urls(region: str | None = None) -> dict:
    """交通情報参照URLを返す。"""
    return {
        "jartic_url": _JARTIC_URL,
        "nexco_urls": _NEXCO_URLS,
        "description": "地震発生後は JARTIC および各 NEXCO の通行規制情報を確認してください。",
        "region": region,
    }


def estimate_road_impact(intensity: float) -> dict:
    """推定震度から道路への影響を推定する。"""
    if intensity >= 6.0:
        return {
            "intensity": intensity,
            "impact_level": "critical",
            "description": "高速道路は全面通行止めの可能性。一般道も寸断リスクあり。",
            "expected_closures": ["高速道路全線", "主要国道", "鉄道全線運転見合わせ"],
        }
    elif intensity >= 5.0:
        return {
            "intensity": intensity,
            "impact_level": "severe",
            "description": "高速道路の一部区間で通行止め。鉄道は運転見合わせ後、点検を経て順次再開。",
            "expected_closures": ["高速道路一部区間", "鉄道（点検後再開）"],
        }
    elif intensity >= 4.0:
        return {
            "intensity": intensity,
            "impact_level": "moderate",
            "description": "鉄道の一時的な運転見合わせ。道路への影響は限定的。",
            "expected_closures": ["鉄道（一時見合わせ）"],
        }
    else:
        return {
            "intensity": intensity,
            "impact_level": "minimal",
            "description": "交通への影響はほぼなし。",
            "expected_closures": [],
        }
