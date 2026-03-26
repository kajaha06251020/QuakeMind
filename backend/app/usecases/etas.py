"""ETAS (Epidemic-Type Aftershock Sequence) 余震予測モデル。

改良大森公式ベース。日本域の標準パラメータ（Ogata 1988）を使用。
"""
import math
import logging
from datetime import datetime, timedelta, timezone

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 日本域標準パラメータ (Ogata 1988)
_MU = 0.5       # 背景発生率 (件/日)
_K = 0.05       # 余震生産性
_ALPHA = 1.0    # マグニチュード依存性
_C = 0.01       # 時間オフセット (日)
_P = 1.1        # 時間減衰指数
_MC = 2.0       # カタログ完全性マグニチュード


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def _triggering_rate(magnitude: float, elapsed_days: float) -> float:
    """1つのイベントが elapsed_days 後に生む余震発生率 (件/日)。"""
    if elapsed_days < 0 or magnitude < _MC:
        return 0.0
    return _K * math.exp(_ALPHA * (magnitude - _MC)) / (elapsed_days + _C) ** _P


def _integrate_rate(magnitude: float, t_start: float, t_end: float, n_steps: int = 100) -> float:
    """トリガー発生率を区間 [t_start, t_end] で数値積分（台形法）。"""
    if t_start >= t_end:
        return 0.0
    dt = (t_end - t_start) / n_steps
    total = 0.0
    for i in range(n_steps + 1):
        t = t_start + i * dt
        rate = _triggering_rate(magnitude, t)
        weight = 0.5 if (i == 0 or i == n_steps) else 1.0
        total += rate * weight * dt
    return total


def etas_forecast(
    events: list[EarthquakeRecord],
    forecast_hours: int = 72,
    m_threshold: float = 4.0,
) -> dict:
    """
    ETAS モデルで今後の余震発生数を予測する。

    Args:
        events: 過去の地震イベントリスト
        forecast_hours: 予測期間（時間）
        m_threshold: 確率計算の閾値マグニチュード

    Returns:
        {"forecast_hours", "expected_events", "probability_m4_plus", "background_rate", "triggered_rate"}
    """
    if not events:
        return {
            "forecast_hours": forecast_hours,
            "expected_events": 0,
            "probability_m4_plus": 0.0,
            "background_rate": _MU,
            "triggered_rate": 0.0,
        }

    timestamps = [_parse_ts(e) for e in events]
    latest = max(timestamps)
    forecast_days = forecast_hours / 24.0

    # 各イベントからのトリガー発生率を積分
    total_triggered = 0.0
    for event, ts in zip(events, timestamps):
        elapsed_start = (latest - ts).total_seconds() / 86400.0
        elapsed_end = elapsed_start + forecast_days
        total_triggered += _integrate_rate(event.magnitude, elapsed_start, elapsed_end)

    # 背景 + トリガー
    expected_total = _MU * forecast_days + total_triggered

    # M >= m_threshold の確率（Gutenberg-Richter: P(M>=m) = 10^(-b*(m-Mc))）
    b = 1.0  # 標準b値
    prob_large = 1.0 - math.exp(-expected_total * 10 ** (-b * (m_threshold - _MC)))

    return {
        "forecast_hours": forecast_hours,
        "expected_events": round(expected_total, 2),
        "probability_m4_plus": round(min(prob_large, 1.0), 4),
        "background_rate": round(_MU * forecast_days, 2),
        "triggered_rate": round(total_triggered, 2),
    }
