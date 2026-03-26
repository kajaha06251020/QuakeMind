"""
Phase 2 地震学解析ユニットテスト
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import (
    _b_value_mle,
    _gk_window,
    _haversine_km,
    _mc_maxc,
    _mc_mbs_ww,
    analyze_gutenberg_richter,
    decluster_gardner_knopoff,
    estimate_mc,
    run_psha,
)


# ── ヘルパー ─────────────────────────────────────────────────────────────────

def _make_event(
    event_id: str,
    magnitude: float,
    lat: float = 35.0,
    lon: float = 135.0,
    depth_km: float = 10.0,
    timestamp: str | None = None,
) -> EarthquakeRecord:
    if timestamp is None:
        timestamp = "2024-01-01T00:00:00+00:00"
    return EarthquakeRecord(
        event_id=event_id,
        magnitude=magnitude,
        latitude=lat,
        longitude=lon,
        depth_km=depth_km,
        timestamp=timestamp,
    )


def _synthetic_gr_catalog(
    n: int = 300,
    b: float = 1.0,
    mc: float = 2.0,
    m_max: float = 7.0,
    seed: int = 42,
) -> list[EarthquakeRecord]:
    """Gutenberg-Richter分布に従う合成カタログを生成"""
    rng = np.random.default_rng(seed)
    # Exponential truncated distribution
    beta = b * math.log(10)
    u = rng.uniform(0, 1, n)
    mags = mc - np.log(1 - u * (1 - np.exp(-beta * (m_max - mc)))) / beta
    mags = np.clip(mags, mc, m_max)

    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    events = []
    for i, m in enumerate(mags):
        ts = (base_time + timedelta(hours=i * 2)).isoformat()
        events.append(
            EarthquakeRecord(
                event_id=f"ev{i:05d}",
                magnitude=round(float(m), 1),
                latitude=35.0 + rng.uniform(-0.5, 0.5),
                longitude=135.0 + rng.uniform(-0.5, 0.5),
                depth_km=10.0,
                timestamp=ts,
            )
        )
    return events


# ── Haversine ────────────────────────────────────────────────────────────────

def test_haversine_same_point():
    assert _haversine_km(35.0, 135.0, 35.0, 135.0) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    # 東京 (35.68, 139.69) ↔ 大阪 (34.69, 135.50) ≈ 395km
    d = _haversine_km(35.68, 139.69, 34.69, 135.50)
    assert 380 < d < 420, f"東京-大阪の距離が異常: {d:.1f}km"


# ── Gardner-Knopoff ウィンドウ ────────────────────────────────────────────────

def test_gk_window_m5():
    dist, time = _gk_window(5.0)
    assert dist == pytest.approx(61.0)
    assert time == pytest.approx(790.0)


def test_gk_window_large():
    dist, time = _gk_window(9.0)
    assert dist == pytest.approx(154.0)
    assert time == pytest.approx(985.0)


# ── デクラスタリング ────────────────────────────────────────────────────────

def test_decluster_trivial_single():
    events = [_make_event("e1", 5.0)]
    result = decluster_gardner_knopoff(events)
    assert result.n_total == 1
    assert result.n_aftershocks == 0


def test_decluster_removes_aftershock():
    """大きいイベントの直後・近傍の小さいイベントが余震として除去される"""
    base = "2024-01-01T12:00:00+00:00"
    after = "2024-01-01T13:00:00+00:00"
    mainshock = _make_event("ms", 6.0, lat=35.0, lon=135.0, timestamp=base)
    aftershock = _make_event("as", 4.5, lat=35.1, lon=135.1, timestamp=after)
    result = decluster_gardner_knopoff([mainshock, aftershock])
    assert "as" in result.aftershock_ids
    assert "ms" in result.mainshock_ids
    assert result.n_aftershocks == 1


def test_decluster_no_removal_far_event():
    """遠方のイベントは余震として除去されない"""
    base = "2024-01-01T12:00:00+00:00"
    after = "2024-01-01T13:00:00+00:00"
    mainshock = _make_event("ms", 6.0, lat=35.0, lon=135.0, timestamp=base)
    distant = _make_event("d1", 4.5, lat=40.0, lon=145.0, timestamp=after)  # 約1100km
    result = decluster_gardner_knopoff([mainshock, distant])
    assert result.n_aftershocks == 0


# ── Mc推定 ────────────────────────────────────────────────────────────────────

def test_mc_maxc_simple():
    # Mc=3.0 付近にピークを作る
    mags = np.array([3.0] * 40 + [3.5] * 20 + [4.0] * 10 + [4.5] * 5 + [5.0] * 2)
    mc = _mc_maxc(mags, bin_size=0.5)
    assert mc == pytest.approx(3.0, abs=0.5)


def test_mc_mbs_returns_float():
    catalog = _synthetic_gr_catalog(n=200, b=1.0, mc=2.0)
    mags = np.array([e.magnitude for e in catalog])
    mc = _mc_mbs_ww(mags)
    assert isinstance(mc, float)
    assert 1.0 <= mc <= 4.0


def test_estimate_mc_structure():
    catalog = _synthetic_gr_catalog(n=200)
    mags = np.array([e.magnitude for e in catalog])
    result = estimate_mc(mags)
    assert result.recommended_mc >= result.mc_maxc - 0.5
    assert result.n_events_above_mc > 0


# ── b値 MLE ────────────────────────────────────────────────────────────────────

def test_b_value_mle_synthetic():
    """合成GRカタログ (b=1.0) のb値がおおよそ正しく推定される"""
    catalog = _synthetic_gr_catalog(n=500, b=1.0, mc=2.0, seed=0)
    mags = np.array([e.magnitude for e in catalog])
    b, db = _b_value_mle(mags, mc=2.0)
    assert 0.7 <= b <= 1.4, f"b値推定が範囲外: {b:.3f}"
    assert db > 0


def test_b_value_mle_insufficient_data():
    """データが少ない場合はデフォルト値を返す"""
    mags = np.array([3.0, 3.5, 4.0, 2.5])  # n=4
    b, db = _b_value_mle(mags, mc=2.0)
    assert b == pytest.approx(1.0)
    assert db == pytest.approx(0.5)


# ── Gutenberg-Richter 解析 ────────────────────────────────────────────────────

def test_analyze_gr_synthetic():
    catalog = _synthetic_gr_catalog(n=300, b=1.0, mc=2.0)
    result = analyze_gutenberg_richter(catalog)
    assert result.n_events >= 10
    assert 0.5 <= result.b_value <= 1.8
    assert result.b_uncertainty > 0
    assert result.a_value > 0


def test_analyze_gr_too_few_events():
    events = [_make_event(f"e{i}", 3.0) for i in range(5)]
    with pytest.raises(ValueError):
        analyze_gutenberg_richter(events)


# ── PSHA ─────────────────────────────────────────────────────────────────────

def test_psha_basic():
    catalog = _synthetic_gr_catalog(n=300, b=1.0, mc=2.0)
    result = run_psha(
        site_lat=35.0, site_lon=135.0,
        events=catalog,
        source_lat=35.5, source_lon=135.5,
    )
    assert result.poe_50yr > 0
    assert result.poe_50yr_2pct >= result.poe_50yr
    assert len(result.hazard_curve) == 30
    assert result.b_value_used > 0


def test_psha_too_few_events():
    events = [_make_event(f"e{i}", 3.0) for i in range(5)]
    with pytest.raises(ValueError):
        run_psha(35.0, 135.0, events, 35.5, 135.5)
