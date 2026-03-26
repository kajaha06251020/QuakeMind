"""地震空白域分析。統計的に地震が来るべきなのに来ていない地域を特定する。"""
import math
import logging
from datetime import datetime, timezone, timedelta

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0

# 日本の主要プレート境界セグメント
_SEGMENTS = [
    {"name": "十勝沖", "lat": 42.0, "lon": 144.0, "expected_interval_years": 80, "last_major": "2003"},
    {"name": "三陸沖北部", "lat": 40.0, "lon": 143.5, "expected_interval_years": 100, "last_major": "1968"},
    {"name": "三陸沖南部", "lat": 38.5, "lon": 143.0, "expected_interval_years": 100, "last_major": "2011"},
    {"name": "茨城県沖", "lat": 36.5, "lon": 141.5, "expected_interval_years": 50, "last_major": "2011"},
    {"name": "房総沖", "lat": 35.0, "lon": 140.5, "expected_interval_years": 200, "last_major": "1923"},
    {"name": "東海", "lat": 34.5, "lon": 138.0, "expected_interval_years": 150, "last_major": "1854"},
    {"name": "南海", "lat": 33.0, "lon": 135.0, "expected_interval_years": 150, "last_major": "1946"},
    {"name": "日向灘", "lat": 32.0, "lon": 132.0, "expected_interval_years": 30, "last_major": "1996"},
]


def analyze_seismic_gaps(events: list[EarthquakeRecord], current_year: int = 2026) -> dict:
    """地震空白域を分析する。"""
    gaps = []

    for seg in _SEGMENTS:
        last_year = int(seg["last_major"])
        elapsed = current_year - last_year
        expected = seg["expected_interval_years"]
        ratio = elapsed / expected  # 1.0 = ちょうど期待周期

        # イベント密度チェック
        nearby = [e for e in events if
            math.sqrt((e.latitude - seg["lat"]) ** 2 + (e.longitude - seg["lon"]) ** 2) * _KM_PER_DEG < 200
            and e.magnitude >= 4.0]

        # BPT分布（対数正規）のハザード関数近似
        alpha = 0.3  # 変動係数（日本の標準値）
        if ratio > 0:
            import scipy.stats as st
            # 条件付き確率 P(next 30yr | elapsed)
            cdf_now = st.lognorm.cdf(elapsed, alpha, scale=expected)
            cdf_future = st.lognorm.cdf(elapsed + 30, alpha, scale=expected)
            prob_30yr = (cdf_future - cdf_now) / (1 - cdf_now) if cdf_now < 1 else 1.0
        else:
            prob_30yr = 0.0

        # 空白域判定
        is_gap = ratio > 0.7 and len(nearby) < 10
        urgency = "critical" if ratio > 1.2 else "high" if ratio > 0.8 else "moderate" if ratio > 0.5 else "low"

        gaps.append({
            "segment": seg["name"],
            "latitude": seg["lat"],
            "longitude": seg["lon"],
            "last_major_event": seg["last_major"],
            "elapsed_years": elapsed,
            "expected_interval_years": expected,
            "elapsed_ratio": round(ratio, 2),
            "probability_next_30yr": round(min(prob_30yr, 1.0), 4),
            "nearby_m4_events": len(nearby),
            "is_seismic_gap": is_gap,
            "urgency": urgency,
        })

    gaps.sort(key=lambda g: g["probability_next_30yr"], reverse=True)

    return {
        "analyzed_segments": len(gaps),
        "identified_gaps": sum(1 for g in gaps if g["is_seismic_gap"]),
        "segments": gaps,
    }
