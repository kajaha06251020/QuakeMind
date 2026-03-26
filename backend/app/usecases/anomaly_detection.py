"""地震活動の異常検知と静穏化検出。"""
import logging
from datetime import datetime, timedelta, timezone

from scipy.stats import poisson

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def detect_anomaly(
    events: list[EarthquakeRecord],
    evaluation_days: int = 7,
) -> dict:
    """
    ポアソン分布に基づく異常活動検知。

    背景期間の平均発生率と直近N日の発生率を比較し、
    ポアソン上側確率で p < 0.05 なら異常と判定。
    """
    if len(events) < 5:
        return {
            "is_anomalous": False,
            "background_rate": 0.0,
            "recent_rate": 0.0,
            "p_value": 1.0,
            "evaluation_days": evaluation_days,
        }

    timestamps = sorted([_parse_ts(e) for e in events])
    last_time = timestamps[-1]
    cutoff = last_time - timedelta(days=evaluation_days)

    background_events = [t for t in timestamps if t < cutoff]
    recent_events = [t for t in timestamps if t >= cutoff]

    if not background_events:
        return {
            "is_anomalous": False,
            "background_rate": 0.0,
            "recent_rate": len(recent_events) / max(evaluation_days, 1),
            "p_value": 1.0,
            "evaluation_days": evaluation_days,
        }

    bg_span_days = max((cutoff - timestamps[0]).total_seconds() / 86400, 1)
    bg_rate = len(background_events) / bg_span_days  # 件/日
    recent_rate = len(recent_events) / max(evaluation_days, 1)

    # ポアソン分布: 背景発生率でevaluation_days間に期待されるイベント数
    expected = bg_rate * evaluation_days
    observed = len(recent_events)

    # 上側確率: P(X >= observed)
    p_value = 1.0 - poisson.cdf(observed - 1, expected) if expected > 0 else 1.0
    is_anomalous = bool(p_value < 0.05 and recent_rate > bg_rate)

    return {
        "is_anomalous": is_anomalous,
        "background_rate": round(bg_rate, 4),
        "recent_rate": round(recent_rate, 4),
        "p_value": round(float(p_value), 6),
        "evaluation_days": evaluation_days,
    }


def detect_quiescence(
    events: list[EarthquakeRecord],
    evaluation_days: int = 30,
) -> dict:
    """
    静穏化検出。

    背景期間の発生率に対して直近発生率が50%以下なら静穏化と判定。
    """
    if len(events) < 5:
        return {
            "is_quiescent": False,
            "background_rate": 0.0,
            "recent_rate": 0.0,
            "ratio": 1.0,
            "evaluation_days": evaluation_days,
        }

    timestamps = sorted([_parse_ts(e) for e in events])
    last_time = timestamps[-1]
    cutoff = last_time - timedelta(days=evaluation_days)

    background_events = [t for t in timestamps if t < cutoff]
    recent_events = [t for t in timestamps if t >= cutoff]

    if not background_events:
        return {
            "is_quiescent": False,
            "background_rate": 0.0,
            "recent_rate": len(recent_events) / max(evaluation_days, 1),
            "ratio": 1.0,
            "evaluation_days": evaluation_days,
        }

    bg_span_days = max((cutoff - timestamps[0]).total_seconds() / 86400, 1)
    bg_rate = len(background_events) / bg_span_days
    recent_rate = len(recent_events) / max(evaluation_days, 1)

    ratio = recent_rate / bg_rate if bg_rate > 0 else 1.0
    is_quiescent = ratio < 0.5 and len(background_events) >= 10

    return {
        "is_quiescent": is_quiescent,
        "background_rate": round(bg_rate, 4),
        "recent_rate": round(recent_rate, 4),
        "ratio": round(ratio, 4),
        "evaluation_days": evaluation_days,
    }
