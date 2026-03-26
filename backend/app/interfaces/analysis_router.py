"""
地震解析 API ルーター (Phase 2)

エンドポイント:
  POST /analysis/decluster   - Gardner-Knopoff デクラスタリング
  POST /analysis/mc          - Mc (完全性マグニチュード) 推定
  POST /analysis/bvalue      - Gutenberg-Richter b値解析
  POST /analysis/gr          - GR関係フルレポート (mc + b + a)
  POST /analysis/psha        - 確率論的地震ハザード解析
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import (
    analyze_gutenberg_richter,
    decluster_gardner_knopoff,
    estimate_mc,
    run_psha,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["seismic-analysis"])


# ── リクエストモデル ────────────────────────────────────────────────────────────

class CatalogRequest(BaseModel):
    """地震カタログ入力 (全エンドポイント共通)"""
    events: list[EarthquakeRecord] = Field(..., min_length=2)


class BValueRequest(CatalogRequest):
    mc_method: str = Field("MBS-WW", description="Mc推定手法: MAXC | MBS-WW | b-positive")
    bin_size: float = Field(0.1, ge=0.01, le=1.0)


class PSHARequest(CatalogRequest):
    site_latitude: float = Field(..., ge=-90, le=90)
    site_longitude: float = Field(..., ge=-180, le=180)
    source_latitude: float = Field(..., ge=-90, le=90)
    source_longitude: float = Field(..., ge=-180, le=180)
    m_max: float = Field(8.5, ge=5.0, le=10.0)
    decluster_first: bool = Field(True, description="解析前にデクラスタリングを実施するか")


# ── エンドポイント ────────────────────────────────────────────────────────────

@router.post("/decluster")
async def decluster(req: CatalogRequest):
    """
    Gardner-Knopoff (1974) デクラスタリング

    カタログから余震を除去し、本震リストを返す。
    """
    try:
        result = decluster_gardner_knopoff(req.events)
        return result
    except Exception as e:
        logger.exception("デクラスタリングエラー")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mc")
async def estimate_completeness_magnitude(req: CatalogRequest):
    """
    完全性マグニチュード (Mc) 推定

    MAXC、MBS-WW (Zhou 2018補正あり)、b-positive の3手法で推定。
    推奨Mcは MBS-WW。
    """
    if len(req.events) < 10:
        raise HTTPException(status_code=400, detail="Mc推定には最低10イベント必要です")
    try:
        mags = np.array([e.magnitude for e in req.events])
        result = estimate_mc(mags)
        return result
    except Exception as e:
        logger.exception("Mc推定エラー")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bvalue")
async def compute_b_value(req: BValueRequest):
    """
    Gutenberg-Richter b値 解析

    MLE (Aki 1965) + Shi & Bolt (1982) 不確かさ。
    Mc推定手法: MAXC / MBS-WW / b-positive
    """
    if len(req.events) < 10:
        raise HTTPException(status_code=400, detail="b値推定には最低10イベント必要です")
    try:
        result = analyze_gutenberg_richter(req.events, mc_method=req.mc_method, bin_size=req.bin_size)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("b値解析エラー")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gr")
async def gutenberg_richter_report(req: BValueRequest):
    """
    Gutenberg-Richter 完全レポート

    b値、a値、Mc、解析イベント数を返す。
    /bvalue と同一だが、将来的に可視化データを追加予定。
    """
    return await compute_b_value(req)


@router.post("/psha")
async def probabilistic_seismic_hazard(req: PSHARequest):
    """
    確率論的地震ハザード解析 (PSHA)

    ポアソン過程 + Boore-Atkinson (2008) 近似 GMPE を使用。
    - 50年超過確率 10% (≈ 475年再現期間) の PGA
    - 50年超過確率 2%  (≈ 2475年再現期間) の PGA
    - ハザードカーブ

    注意: 本実装は教育・研究用の簡易モデルです。
          本番ハザード評価にはOpenQuake Engineを使用してください。
    """
    if len(req.events) < 10:
        raise HTTPException(status_code=400, detail="PSHAには最低10イベント必要です")
    try:
        events = req.events
        if req.decluster_first:
            dc = decluster_gardner_knopoff(events)
            ms_ids = set(dc.mainshock_ids)
            events = [e for e in events if e.event_id in ms_ids]
            if len(events) < 10:
                raise HTTPException(
                    status_code=400,
                    detail=f"デクラスタ後のイベント数が不足 (n={len(events)}). decluster_first=false で再試行してください"
                )

        result = run_psha(
            site_lat=req.site_latitude,
            site_lon=req.site_longitude,
            events=events,
            source_lat=req.source_latitude,
            source_lon=req.source_longitude,
            m_max=req.m_max,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PSHAエラー")
        raise HTTPException(status_code=500, detail=str(e))
