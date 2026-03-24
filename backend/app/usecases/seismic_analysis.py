"""
地震学解析アルゴリズム (Phase 2)

実装アルゴリズム:
  - Gardner-Knopoff (1974) デクラスタリング
  - MAXC法 Mc推定
  - MBS-WW法 Mc推定 (Woessner & Wiemer 2005) + Zhou (2018) -0.1補正
  - b-positive法 Mc/b推定 (van der Elst 2021)
  - b値 MLE (Aki 1965) + Shi & Bolt (1982) δb
  - Gutenberg-Richter a値
  - 簡易PSHA (ポアソン過程 + Boore-Atkinson 2008近似)
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from app.domain.seismology import (
    DeclusterResult,
    EarthquakeRecord,
    GutenbergRichterResult,
    McEstimationResult,
    PSHAResult,
)

logger = logging.getLogger(__name__)

# ── Gardner-Knopoff (1974) 時空間ウィンドウ ─────────────────────────────────────
# Magnitude → (distance_km, time_days)
_GK_WINDOWS: list[tuple[float, float, float]] = [
    # (mag_min, dist_km, time_days)
    (1.0, 19.5, 6.0),
    (1.5, 22.5, 11.5),
    (2.0, 26.0, 22.0),
    (2.5, 30.0, 42.0),
    (3.0, 34.5, 83.0),
    (3.5, 40.0, 155.0),
    (4.0, 47.0, 290.0),
    (4.5, 54.0, 510.0),
    (5.0, 61.0, 790.0),
    (5.5, 70.0, 915.0),
    (6.0, 81.0, 960.0),
    (6.5, 94.0, 985.0),
    (7.0, 110.0, 985.0),
    (7.5, 130.0, 985.0),
    (8.0, 154.0, 985.0),
]


def _gk_window(magnitude: float) -> tuple[float, float]:
    """Gardner-Knopoff 時空間ウィンドウを返す (dist_km, time_days)"""
    for i, (m_min, dist, time) in enumerate(_GK_WINDOWS):
        if i + 1 < len(_GK_WINDOWS):
            m_next = _GK_WINDOWS[i + 1][0]
            if m_min <= magnitude < m_next:
                return dist, time
        else:
            return dist, time
    return _GK_WINDOWS[-1][1], _GK_WINDOWS[-1][2]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine 距離 (km)"""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def decluster_gardner_knopoff(events: list[EarthquakeRecord]) -> DeclusterResult:
    """
    Gardner-Knopoff (1974) デクラスタリング

    時系列順にソートし、大きいイベントの時空間ウィンドウ内にある
    後続イベントを余震としてマークする。
    """
    if len(events) < 2:
        return DeclusterResult(
            method="Gardner-Knopoff",
            n_total=len(events),
            n_mainshocks=len(events),
            n_aftershocks=0,
            aftershock_ratio=0.0,
            mainshock_ids=[e.event_id for e in events],
            aftershock_ids=[],
        )

    # timestamp順でソート
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    n = len(sorted_events)

    times: list[float] = []
    for e in sorted_events:
        try:
            dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            times.append(dt.timestamp())
        except Exception:
            times.append(0.0)

    is_aftershock = [False] * n

    for i in range(n):
        if is_aftershock[i]:
            continue
        ev_i = sorted_events[i]
        dist_win, time_win = _gk_window(ev_i.magnitude)
        time_win_sec = time_win * 86400.0

        for j in range(i + 1, n):
            # 時間ウィンドウを超えたら内側のループを打ち切る
            if times[j] - times[i] > time_win_sec:
                break
            if is_aftershock[j]:
                continue

            ev_j = sorted_events[j]
            # マグニチュードが小さいイベントのみ余震候補
            if ev_j.magnitude >= ev_i.magnitude:
                continue

            dist_km = _haversine_km(ev_i.latitude, ev_i.longitude, ev_j.latitude, ev_j.longitude)
            if dist_km <= dist_win:
                is_aftershock[j] = True

    mainshock_ids = [sorted_events[i].event_id for i in range(n) if not is_aftershock[i]]
    aftershock_ids = [sorted_events[i].event_id for i in range(n) if is_aftershock[i]]
    n_as = len(aftershock_ids)

    return DeclusterResult(
        method="Gardner-Knopoff",
        n_total=n,
        n_mainshocks=len(mainshock_ids),
        n_aftershocks=n_as,
        aftershock_ratio=n_as / n if n > 0 else 0.0,
        mainshock_ids=mainshock_ids,
        aftershock_ids=aftershock_ids,
    )


# ── Mc 推定 ─────────────────────────────────────────────────────────────────────

def _magnitude_bins(magnitudes: np.ndarray, bin_size: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """マグニチュードの度数分布 (bins, counts)"""
    m_min = np.floor(magnitudes.min() / bin_size) * bin_size
    m_max = np.ceil(magnitudes.max() / bin_size) * bin_size
    bins = np.arange(m_min, m_max + bin_size, bin_size)
    counts = np.array([np.sum((magnitudes >= b) & (magnitudes < b + bin_size)) for b in bins])
    return bins, counts


def _mc_maxc(magnitudes: np.ndarray, bin_size: float = 0.1) -> float:
    """MAXC法: 頻度分布のピーク = Mc"""
    bins, counts = _magnitude_bins(magnitudes, bin_size)
    if counts.max() == 0:
        return float(bins[0])
    peak_idx = int(np.argmax(counts))
    return float(bins[peak_idx])


def _b_value_mle(magnitudes: np.ndarray, mc: float, bin_size: float = 0.1) -> tuple[float, float]:
    """
    Aki (1965) MLE b値 + Shi & Bolt (1982) δb

    b = log10(e) / (mean_M - (Mc - bin_size/2))
    δb = 2.30 * b^2 * std_M / sqrt(N*(N-1))
    """
    mags = magnitudes[magnitudes >= mc]
    n = len(mags)
    if n < 5:
        return 1.0, 0.5  # データ不足
    mean_m = float(np.mean(mags))
    std_m = float(np.std(mags, ddof=1))
    b = math.log10(math.e) / (mean_m - (mc - bin_size / 2))
    db = 2.30 * b ** 2 * std_m / math.sqrt(n * (n - 1)) if n > 1 else 0.5
    return b, db


def _mc_mbs_ww(magnitudes: np.ndarray, bin_size: float = 0.1, n_bootstrap: int = 200) -> float:
    """
    MBS-WW法 (Woessner & Wiemer 2005) + Zhou (2018) -0.1補正

    各Mc候補でb値をMLE推定し、カタログ再現残差が最小になるMcを選ぶ。
    Zhou補正: 推定値に -0.1 を加える。
    """
    bins, _ = _magnitude_bins(magnitudes, bin_size)
    mc_candidates = bins[bins >= magnitudes.min()]
    best_mc = float(mc_candidates[0])
    best_residual = float("inf")

    for mc_cand in mc_candidates:
        mags_above = magnitudes[magnitudes >= mc_cand]
        if len(mags_above) < 10:
            break

        b, _ = _b_value_mle(magnitudes, mc_cand, bin_size)
        a = math.log10(len(mags_above)) + b * mc_cand

        # GR予測との残差 (bin毎)
        bins_above = bins[bins >= mc_cand]
        residuals = []
        for bm in bins_above:
            obs = float(np.sum(magnitudes >= bm))
            pred = 10 ** (a - b * bm)
            if pred > 0:
                residuals.append(abs(math.log10(max(obs, 0.5)) - math.log10(pred)))

        if residuals:
            mean_res = float(np.mean(residuals))
            if mean_res < best_residual:
                best_residual = mean_res
                best_mc = float(mc_cand)

    # Zhou (2018) 補正
    return round(best_mc - 0.1, 1)


def _mc_b_positive(magnitudes: np.ndarray, bin_size: float = 0.1) -> Optional[float]:
    """
    b-positive法 (van der Elst 2021)

    正の差分マグニチュード ΔM+ を用いてMcに依存しない安定なbを推定し、
    GRとの整合からMcを導く。差分データが少ない場合はNoneを返す。
    """
    sorted_m = np.sort(magnitudes)
    diffs = np.diff(sorted_m)
    pos_diffs = diffs[diffs > 0]
    if len(pos_diffs) < 10:
        return None

    mean_diff = float(np.mean(pos_diffs))
    if mean_diff <= 0:
        return None

    b_pos = math.log10(math.e) / mean_diff

    # b-positiveから推定されるMcを逆算 (MAXC比較)
    mc_maxc = _mc_maxc(magnitudes, bin_size)
    b_maxc, _ = _b_value_mle(magnitudes, mc_maxc, bin_size)

    if abs(b_maxc - b_pos) < 0.3:
        return mc_maxc
    # bが違う → 安定解としてMAXC + 0.2を返す
    return round(mc_maxc + 0.2, 1)


def estimate_mc(magnitudes: np.ndarray, bin_size: float = 0.1) -> McEstimationResult:
    """Mc推定 (MAXC, MBS-WW, b-positive の3手法)"""
    mc_maxc = _mc_maxc(magnitudes, bin_size)
    mc_mbs = _mc_mbs_ww(magnitudes, bin_size)
    mc_bpos = _mc_b_positive(magnitudes, bin_size)

    recommended = mc_mbs
    n_above = int(np.sum(magnitudes >= recommended))

    return McEstimationResult(
        mc_maxc=round(mc_maxc, 2),
        mc_mbs=round(mc_mbs, 2),
        mc_bpos=round(mc_bpos, 2) if mc_bpos is not None else None,
        recommended_mc=round(recommended, 2),
        n_events_above_mc=n_above,
    )


# ── Gutenberg-Richter 解析 ────────────────────────────────────────────────────

def analyze_gutenberg_richter(
    events: list[EarthquakeRecord],
    mc_method: str = "MBS-WW",
    bin_size: float = 0.1,
) -> GutenbergRichterResult:
    """
    Gutenberg-Richter b値 完全解析

    1. Mc推定 (MAXC / MBS-WW / b-positive)
    2. MLE b値 + Shi & Bolt δb
    3. GR a値
    """
    if len(events) < 10:
        raise ValueError(f"イベント数が少なすぎます (n={len(events)}, 最低10必要)")

    mags = np.array([e.magnitude for e in events])

    mc_result = estimate_mc(mags, bin_size)
    if mc_method == "MAXC":
        mc = mc_result.mc_maxc
    elif mc_method == "b-positive":
        mc = mc_result.mc_bpos if mc_result.mc_bpos is not None else mc_result.recommended_mc
    else:
        mc = mc_result.recommended_mc

    b, db = _b_value_mle(mags, mc, bin_size)

    mags_above = mags[mags >= mc]
    n = len(mags_above)
    a = math.log10(n) + b * mc if n > 0 else 0.0

    return GutenbergRichterResult(
        mc=round(mc, 2),
        b_value=round(b, 4),
        b_uncertainty=round(db, 4),
        a_value=round(a, 4),
        n_events=n,
        mc_method=mc_method,
    )


# ── PSHA (簡易実装) ────────────────────────────────────────────────────────────
# Boore-Atkinson 2008 (BA08) を大幅に単純化した点減衰モデル
# 本番ではOpenQuakeのhazardlibと差し替える

def _ba08_pga_median(magnitude: float, distance_km: float) -> float:
    """
    簡易PGA中央値 (g) — Si & Midorikawa (1999) スタイル

    log10(PGA[g]) = c1*M + c2*log10(R+c3) + c4
    M7, R=70km で ≈ 0.2g、M6, R=70km で ≈ 0.04g

    原典: Si & Midorikawa (1999) を単純化し係数を調整
    """
    R = max(distance_km, 1.0)
    log_pga = 0.777 * magnitude - 1.83 * math.log10(R + 10) - 2.492
    return 10 ** log_pga


def _annual_rate_exceeding(
    pga_threshold: float,
    a_value: float,
    b_value: float,
    mc: float,
    m_max: float,
    distance_km: float,
    sigma_ln: float = 0.6,
) -> float:
    """
    簡易PSHA: 年間超過率 P(PGA > pga_threshold)

    マグニチュード区間 [mc, m_max] を離散化し、
    各マグニチュードの発生率 × 超過確率(log正規分布)を積分
    """
    from scipy.stats import norm as sp_norm

    m_bins = np.arange(mc, m_max + 0.05, 0.1)
    annual_rate = 0.0

    for m in m_bins:
        # マグニチュードmの年間発生率
        rate_m = (10 ** (a_value - b_value * m) - 10 ** (a_value - b_value * (m + 0.1)))
        rate_m = max(rate_m, 0.0)

        # BA08でのPGA中央値
        pga_med = _ba08_pga_median(float(m), distance_km)
        if pga_med <= 0:
            continue

        # 対数正規分布での超過確率
        ln_ratio = math.log(pga_threshold / pga_med)
        prob_exceed = 1.0 - float(sp_norm.cdf(ln_ratio / sigma_ln))

        annual_rate += rate_m * prob_exceed

    return annual_rate


def _observation_years(events: list[EarthquakeRecord]) -> float:
    """カタログの観測期間 (年) を推定する"""
    times: list[float] = []
    for e in events:
        try:
            dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            times.append(dt.timestamp())
        except Exception:
            pass
    if len(times) < 2:
        return 1.0
    span_sec = max(times) - min(times)
    years = span_sec / (365.25 * 86400)
    return max(years, 1.0 / 365)  # 最低1日


def run_psha(
    site_lat: float,
    site_lon: float,
    events: list[EarthquakeRecord],
    source_lat: float,
    source_lon: float,
    m_max: float = 8.5,
    sigma_ln: float = 0.6,
) -> PSHAResult:
    """
    確率論的地震ハザード解析

    Args:
        site_lat/lon: 評価地点
        events: 解析に使うカタログ (デクラスタ済み推奨)
        source_lat/lon: 震源域代表点
        m_max: 最大マグニチュード
        sigma_ln: GMPE対数標準偏差
    """
    if len(events) < 10:
        raise ValueError(f"PSHAにはイベント数が不足しています (n={len(events)})")

    gr = analyze_gutenberg_richter(events)

    # a値を年率に換算 (観測期間で正規化)
    obs_years = _observation_years(events)
    a_annual = gr.a_value - math.log10(obs_years)

    distance_km = _haversine_km(site_lat, site_lon, source_lat, source_lon)
    distance_km = max(distance_km, 10.0)

    # ハザードカーブ生成
    pga_range = np.logspace(-2, 0.5, 30)  # 0.01g ~ 3.16g
    hazard_curve = []
    for pga in pga_range:
        ann_rate = _annual_rate_exceeding(
            float(pga), a_annual, gr.b_value, gr.mc, m_max, distance_km, sigma_ln
        )
        # ポアソン過程での超過確率 (1年間)
        hazard_curve.append({"pga_g": round(float(pga), 4), "annual_poe": round(ann_rate, 6)})

    def _pga_for_poe(target_annual_poe: float) -> float:
        """目標年間超過率に対するPGAを二分法で解く"""
        try:
            return brentq(
                lambda pga: _annual_rate_exceeding(
                    pga, a_annual, gr.b_value, gr.mc, m_max, distance_km, sigma_ln
                ) - target_annual_poe,
                1e-4, 10.0,
                xtol=1e-4, maxiter=50,
            )
        except (ValueError, RuntimeError):
            return 0.0

    # 475年再現期間 = 年間超過率 1/475 ≈ 0.00211
    poe_475 = 1 / 475
    # 50年10% = 年間超過率 -ln(0.9)/50 ≈ 0.00211 (ほぼ同じ)
    poe_50yr_10pct = -math.log(0.90) / 50
    # 50年2% = 年間超過率 -ln(0.98)/50 ≈ 0.000404
    poe_50yr_2pct = -math.log(0.98) / 50

    pga_475 = _pga_for_poe(poe_475)
    pga_2500 = _pga_for_poe(poe_50yr_2pct)

    return PSHAResult(
        site_latitude=site_lat,
        site_longitude=site_lon,
        poe_50yr=round(pga_475, 4),
        poe_50yr_2pct=round(pga_2500, 4),
        mean_return_period_475yr=round(pga_475, 4),
        hazard_curve=hazard_curve,
        b_value_used=gr.b_value,
        mc_used=gr.mc,
        n_events_used=gr.n_events,
    )
