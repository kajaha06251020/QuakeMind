"""ドメインモデル。外側（インフラ・UI）に依存しない純粋な定義。"""
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel


class EarthquakeEvent(BaseModel):
    event_id: str
    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    region: str
    timestamp: datetime
    source: str = "p2p"


class RiskScore(BaseModel):
    event_id: str
    estimated_intensity: float
    aftershock_prob_72h: float
    tsunami_flag: bool
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    computed_at: datetime


class EvacuationRoute(BaseModel):
    event_id: str
    danger_radius_km: float
    safe_direction: str
    notes: str
    generated_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AlertMessage(BaseModel):
    event_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ja_text: str
    en_text: str
    is_fallback: bool = False
    timestamp: datetime


# ─── LangGraph EventState ─────────────────────────────────────────────────────

from typing import TypedDict


class EventState(TypedDict):
    event_id: str
    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    region: str
    timestamp: str
    estimated_intensity: float
    aftershock_prob_72h: float
    tsunami_flag: bool
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    danger_radius_km: float
    safe_direction: str
    notes: str
    ja_text: str
    en_text: str
    is_fallback: bool
    error: str


# ─── severity マッピング ───────────────────────────────────────────────────────

def compute_severity(
    estimated_intensity: float,
    aftershock_prob_72h: float,
    tsunami_flag: bool,
) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    if estimated_intensity >= 6.0 or tsunami_flag:
        return "CRITICAL"
    if estimated_intensity >= 5.0 or aftershock_prob_72h >= 0.6:
        return "HIGH"
    if estimated_intensity >= 4.0 or aftershock_prob_72h >= 0.3:
        return "MEDIUM"
    return "LOW"
