"""
地震学解析の結果モデル (Phase 2)
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class EarthquakeRecord(BaseModel):
    """地震カタログの1レコード"""
    event_id: str
    magnitude: float
    latitude: float
    longitude: float
    depth_km: float
    timestamp: str  # ISO 8601
    is_aftershock: bool = False


class GutenbergRichterResult(BaseModel):
    """Gutenberg-Richter b値解析結果"""
    mc: float = Field(description="完全性マグニチュード Mc")
    b_value: float = Field(description="b値 (傾き)")
    b_uncertainty: float = Field(description="b値の不確かさ δb (Shi & Bolt 1982)")
    a_value: float = Field(description="a値 (切片)")
    n_events: int = Field(description="解析に使用したイベント数")
    mc_method: str = Field(description="Mc推定手法")


class DeclusterResult(BaseModel):
    """デクラスタリング結果"""
    method: str = Field(description="使用した手法 (Gardner-Knopoff)")
    n_total: int = Field(description="元のカタログのイベント数")
    n_mainshocks: int = Field(description="本震数")
    n_aftershocks: int = Field(description="余震数")
    aftershock_ratio: float = Field(description="余震率 [0-1]")
    mainshock_ids: list[str] = Field(description="本震のイベントIDリスト")
    aftershock_ids: list[str] = Field(description="余震のイベントIDリスト")


class McEstimationResult(BaseModel):
    """Mc (完全性マグニチュード) 推定結果"""
    mc_maxc: float = Field(description="MAXC法によるMc")
    mc_mbs: float = Field(description="MBS-WW法によるMc")
    mc_bpos: Optional[float] = Field(None, description="b-positive法によるMc")
    recommended_mc: float = Field(description="推奨Mc (MBS-WW)")
    n_events_above_mc: int = Field(description="Mc以上のイベント数")


class PSHAResult(BaseModel):
    """確率論的地震ハザード解析 (PSHA) 結果"""
    site_latitude: float
    site_longitude: float
    poe_50yr: float = Field(description="50年超過確率 10% に対する地動加速度 [g]")
    poe_50yr_2pct: float = Field(description="50年超過確率 2% に対する地動加速度 [g]")
    mean_return_period_475yr: float = Field(description="475年再現期間 (10%/50yr) の PGA [g]")
    hazard_curve: list[dict] = Field(description="ハザードカーブ [[pga_g, annual_poe], ...]")
    b_value_used: float
    mc_used: float
    n_events_used: int
