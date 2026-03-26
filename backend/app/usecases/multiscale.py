"""マルチスケール統一分析。秒〜世紀スケールを1つのフレームワークで扱う。"""
import math
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def multiscale_analysis(events: list[EarthquakeRecord]) -> dict:
    if len(events) < 10:
        return {"error": "最低10イベント必要"}

    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except: return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_e = sorted(events, key=_ts)
    timestamps = [_ts(e) for e in sorted_e]
    mags = [e.magnitude for e in sorted_e]

    span_days = max((timestamps[-1] - timestamps[0]).total_seconds() / 86400, 1)

    scales = {}

    # 時間スケール: 分
    if span_days >= 1:
        inter_event_times = [(timestamps[i+1] - timestamps[i]).total_seconds() / 60 for i in range(len(timestamps)-1)]
        scales["minutes"] = {
            "description": "イベント間隔分析",
            "mean_interval_min": round(float(np.mean(inter_event_times)), 2) if inter_event_times else 0,
            "min_interval_min": round(float(np.min(inter_event_times)), 2) if inter_event_times else 0,
            "cv": round(float(np.std(inter_event_times) / max(np.mean(inter_event_times), 0.01)), 3) if inter_event_times else 0,
        }

    # 日スケール
    daily = Counter(t.date() for t in timestamps)
    daily_counts = list(daily.values())
    scales["daily"] = {
        "description": "日別発生頻度",
        "mean_per_day": round(len(events) / max(span_days, 1), 2),
        "max_per_day": max(daily_counts) if daily_counts else 0,
        "active_days": len(daily),
        "total_days": int(span_days),
    }

    # 週スケール
    if span_days >= 14:
        weekly = Counter((t - timestamps[0]).days // 7 for t in timestamps)
        weekly_counts = list(weekly.values())
        trend = "increasing" if len(weekly_counts) >= 3 and weekly_counts[-1] > weekly_counts[0] * 1.5 else "stable" if len(weekly_counts) >= 3 else "insufficient"
        scales["weekly"] = {
            "description": "週別トレンド",
            "mean_per_week": round(float(np.mean(weekly_counts)), 1),
            "trend": trend,
            "n_weeks": len(weekly_counts),
        }

    # 月スケール
    if span_days >= 60:
        monthly = Counter((t - timestamps[0]).days // 30 for t in timestamps)
        monthly_counts = list(monthly.values())
        scales["monthly"] = {
            "description": "月別パターン",
            "mean_per_month": round(float(np.mean(monthly_counts)), 1),
            "variability": round(float(np.std(monthly_counts) / max(np.mean(monthly_counts), 0.01)), 3),
        }

    # マグニチュード-時間関係
    mag_time_corr = float(np.corrcoef(range(len(mags)), mags)[0, 1]) if len(mags) > 2 else 0

    # 総合評価
    cv = scales.get("minutes", {}).get("cv", 1)
    if cv < 0.5:
        pattern = "quasi_periodic"
    elif cv < 1.5:
        pattern = "poisson_like"
    else:
        pattern = "clustered"

    return {
        "n_events": len(events),
        "time_span_days": round(span_days, 1),
        "scales": scales,
        "magnitude_time_correlation": round(mag_time_corr, 4),
        "temporal_pattern": pattern,
    }
