"""カスタムアラートルール。

ユーザー定義の複合条件でアラート発火を判定する。
例: 「M5以上かつ東京から100km以内」
"""
import math
import logging
from typing import Optional

from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2*R*math.asin(min(1.0, math.sqrt(a)))


class AlertRule:
    """カスタムアラートルール。"""
    def __init__(
        self,
        name: str,
        min_magnitude: Optional[float] = None,
        max_depth_km: Optional[float] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        regions: Optional[list[str]] = None,
    ):
        self.name = name
        self.min_magnitude = min_magnitude
        self.max_depth_km = max_depth_km
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = radius_km
        self.regions = regions

    def matches(self, event: EarthquakeEvent) -> bool:
        if self.min_magnitude is not None and event.magnitude < self.min_magnitude:
            return False
        if self.max_depth_km is not None and event.depth_km > self.max_depth_km:
            return False
        if self.regions and event.region not in self.regions:
            return False
        if self.center_lat is not None and self.center_lon is not None and self.radius_km is not None:
            dist = _haversine_km(self.center_lat, self.center_lon, event.latitude, event.longitude)
            if dist > self.radius_km:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "min_magnitude": self.min_magnitude,
            "max_depth_km": self.max_depth_km,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "radius_km": self.radius_km,
            "regions": self.regions,
        }


def evaluate_rules(event: EarthquakeEvent, rules: list[AlertRule]) -> list[dict]:
    """イベントに対して全ルールを評価し、マッチしたルールを返す。"""
    matched = []
    for rule in rules:
        if rule.matches(event):
            matched.append(rule.to_dict())
    return matched
