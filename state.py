from typing import Annotated, TypedDict, Literal
from datetime import datetime
from pydantic import BaseModel
import operator


# ─── Pydantic データモデル ────────────────────────────────────────────────────

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


class AlertMessage(BaseModel):
    event_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ja_text: str
    en_text: str
    is_fallback: bool = False
    timestamp: datetime


# ─── LangGraph 状態（1イベント処理サイクル） ──────────────────────────────────
# Monitor は FastAPI lifespan ループで動き、新規イベントごとに graph.ainvoke() を呼ぶ。
# この State は predict → route → personal の処理を通じて受け渡される。

class EventState(TypedDict):
    # 入力（Monitor から渡される EarthquakeEvent の各フィールド）
    event_id: str
    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    region: str
    timestamp: str  # ISO8601 文字列

    # Predict Agent が書き込む
    estimated_intensity: float
    aftershock_prob_72h: float
    tsunami_flag: bool
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # Route Agent が書き込む
    danger_radius_km: float
    safe_direction: str
    notes: str

    # Personal Agent が書き込む
    ja_text: str
    en_text: str
    is_fallback: bool

    # エラー
    error: str


# severity マッピング（仕様書準拠）
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
