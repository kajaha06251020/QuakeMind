"""予測コーディング。予測誤差（サプライズ）を前兆検出に活用する。"""
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import Counter
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def compute_surprise(events: list[EarthquakeRecord], window_days: int = 7) -> dict:
    if len(events) < 20:
        return {"error": "最低20イベント必要"}

    def _ts(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_e = sorted(events, key=_ts)
    timestamps = [_ts(e) for e in sorted_e]
    first, last = timestamps[0].date(), timestamps[-1].date()
    n_days = (last - first).days + 1
    if n_days < window_days * 3:
        return {"error": "期間が短すぎます"}

    daily = Counter(t.date() for t in timestamps)
    counts = np.array([daily.get(first + timedelta(days=d), 0) for d in range(n_days)], dtype=float)

    # 予測: 過去window_days日の移動平均
    surprises = []
    for i in range(window_days, n_days):
        predicted = float(np.mean(counts[i - window_days:i]))
        actual = float(counts[i])
        surprise = abs(actual - predicted) / max(predicted, 0.5)
        surprises.append({
            "day_index": i,
            "date": (first + timedelta(days=i)).isoformat(),
            "predicted": round(predicted, 2),
            "actual": int(actual),
            "surprise": round(surprise, 4),
        })

    surprise_vals = [s["surprise"] for s in surprises]
    mean_surprise = float(np.mean(surprise_vals))
    recent_surprise = (
        float(np.mean(surprise_vals[-window_days:]))
        if len(surprise_vals) >= window_days
        else mean_surprise
    )

    # 高サプライズ期間の検出
    threshold = mean_surprise + 2 * float(np.std(surprise_vals))
    high_surprise_periods = [s for s in surprises if s["surprise"] > threshold]

    return {
        "mean_surprise": round(mean_surprise, 4),
        "recent_surprise": round(recent_surprise, 4),
        "surprise_ratio": round(recent_surprise / max(mean_surprise, 0.01), 2),
        "n_high_surprise_days": len(high_surprise_periods),
        "alert": recent_surprise > threshold,
        "alert_message": "直近の活動が予測を大幅に上回っている" if recent_surprise > threshold else "予測範囲内",
        "recent_surprises": surprises[-10:],
    }
