"""日別地震発生数の時系列予測（指数平滑法）。"""
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def _exponential_smoothing(series: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """単純指数平滑法。"""
    result = np.zeros_like(series, dtype=float)
    result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def forecast_daily_counts(
    events: list[EarthquakeRecord],
    forecast_days: int = 7,
    alpha: float = 0.3,
) -> dict:
    """
    日別地震発生数を指数平滑法で予測する。

    Returns:
        {"forecast": [{"date": "YYYY-MM-DD", "expected_count": float}, ...], "historical_mean": float}
    """
    if not events:
        return {"forecast": [], "historical_mean": 0.0}

    timestamps = [_parse_ts(e) for e in events]
    dates = [t.date() for t in timestamps]
    date_counts = Counter(dates)

    first_date = min(dates)
    last_date = max(dates)

    # 日別カウント配列を作成（欠損日は0）
    n_days = (last_date - first_date).days + 1
    if n_days < 1:
        n_days = 1
    daily = np.zeros(n_days)
    for d, count in date_counts.items():
        idx = (d - first_date).days
        if 0 <= idx < n_days:
            daily[idx] = count

    historical_mean = float(daily.mean())

    # 指数平滑
    if n_days >= 3:
        smoothed = _exponential_smoothing(daily, alpha=alpha)
        last_level = smoothed[-1]
    else:
        last_level = historical_mean

    # 予測: 最終レベルを使用（単純指数平滑は水平予測）
    forecast = []
    for i in range(forecast_days):
        forecast_date = last_date + timedelta(days=i + 1)
        forecast.append({
            "date": forecast_date.isoformat(),
            "expected_count": round(max(0.0, last_level), 2),
        })

    return {
        "forecast": forecast,
        "historical_mean": round(historical_mean, 2),
    }
