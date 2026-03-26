"""前震パターンマッチング。

過去の大地震前の「加速的活動増加」パターンとの類似度を計算。
テンプレート: 30日間の日別イベント数が単調増加するパターン。
"""
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 前震テンプレート: 30日間で加速的に増加するパターン（正規化済み）
_FORESHOCK_TEMPLATE = np.array([1, 1, 1, 1, 1, 2, 2, 2, 2, 2,
                                 3, 3, 3, 3, 3, 4, 4, 4, 4, 4,
                                 5, 5, 6, 6, 7, 7, 8, 9, 10, 12], dtype=float)
_FORESHOCK_TEMPLATE = _FORESHOCK_TEMPLATE / np.linalg.norm(_FORESHOCK_TEMPLATE)


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def match_foreshock_pattern(
    events: list[EarthquakeRecord],
    window_days: int = 30,
) -> dict:
    """
    直近 window_days 日間の活動パターンと前震テンプレートの類似度を計算。

    Returns:
        {"similarity_score": float, "pattern_type": str, "alert_level": str, "daily_counts": list}
    """
    if len(events) < 5:
        return {
            "similarity_score": 0.0,
            "pattern_type": "insufficient_data",
            "alert_level": "normal",
            "daily_counts": [],
        }

    timestamps = [_parse_ts(e) for e in events]
    last_time = max(timestamps)
    start_time = last_time - timedelta(days=window_days)

    recent = [t for t in timestamps if t >= start_time]
    if len(recent) < 5:
        return {
            "similarity_score": 0.0,
            "pattern_type": "insufficient_data",
            "alert_level": "normal",
            "daily_counts": [],
        }

    # 日別カウント（30日分）
    date_counts = Counter(t.date() for t in recent)
    start_date = start_time.date()
    daily = np.array([date_counts.get(start_date + timedelta(days=d), 0) for d in range(window_days)], dtype=float)

    # テンプレートとのコサイン類似度
    template = _FORESHOCK_TEMPLATE[:window_days]
    if len(template) < window_days:
        template = np.pad(template, (0, window_days - len(template)))

    similarity = _cosine_similarity(daily, template)

    # パターン分類
    if similarity >= 0.7:
        pattern_type = "accelerating"
        alert_level = "elevated"
    elif similarity >= 0.4:
        pattern_type = "moderately_increasing"
        alert_level = "watch"
    else:
        pattern_type = "normal"
        alert_level = "normal"

    return {
        "similarity_score": round(similarity, 4),
        "pattern_type": pattern_type,
        "alert_level": alert_level,
        "daily_counts": daily.tolist(),
    }
