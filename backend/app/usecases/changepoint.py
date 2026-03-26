"""ベイズ変化点検出。b値や発生率の変化時点を統計的に検出する。

CUSUM + ベイズ事後確率。
"""
import math
import logging
from datetime import datetime, timezone, timedelta

import numpy as np
from scipy.stats import poisson

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def detect_rate_changepoints(
    events: list[EarthquakeRecord],
    window_days: int = 7,
    significance: float = 0.05,
) -> dict:
    """発生率の変化点を検出する。

    スライディングウィンドウで日別カウントを作り、
    各時点で「ここが変化点である事後確率」を計算する。
    """
    if len(events) < 20:
        return {"changepoints": [], "n_events": len(events)}

    def _parse(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except:
            return datetime(2000, 1, 1, tzinfo=timezone.utc)

    timestamps = sorted([_parse(e) for e in events])
    first = timestamps[0].date()
    last = timestamps[-1].date()
    n_days = (last - first).days + 1

    if n_days < 14:
        return {"changepoints": [], "n_events": len(events)}

    # 日別カウント
    from collections import Counter
    date_counts = Counter(t.date() for t in timestamps)
    daily = np.array([date_counts.get(first + timedelta(days=d), 0) for d in range(n_days)], dtype=float)

    # ベイズ変化点検出
    changepoints = []
    n = len(daily)

    for t in range(window_days, n - window_days):
        before = daily[max(0, t - window_days):t]
        after = daily[t:min(n, t + window_days)]

        if len(before) < 3 or len(after) < 3:
            continue

        mean_before = float(np.mean(before))
        mean_after = float(np.mean(after))

        # ベイズ因子近似: 2つのポアソン率が異なるモデル vs 同じモデル
        if mean_before == 0 and mean_after == 0:
            continue

        # 対数尤度比
        ll_same = sum(poisson.logpmf(int(x), max(np.mean(daily), 0.01)) for x in np.concatenate([before, after]))
        ll_diff = (
            sum(poisson.logpmf(int(x), max(mean_before, 0.01)) for x in before) +
            sum(poisson.logpmf(int(x), max(mean_after, 0.01)) for x in after)
        )

        log_bf = ll_diff - ll_same  # ベイズ因子の対数
        posterior_prob = 1 / (1 + math.exp(-log_bf))  # ロジスティック近似

        if posterior_prob > (1 - significance):
            date = (first + timedelta(days=t)).isoformat()
            changepoints.append({
                "date": date,
                "day_index": t,
                "rate_before": round(mean_before, 3),
                "rate_after": round(mean_after, 3),
                "change_ratio": round(mean_after / max(mean_before, 0.01), 2),
                "posterior_probability": round(posterior_prob, 4),
                "type": "increase" if mean_after > mean_before else "decrease",
            })

    # 隣接する変化点をマージ（7日以内は1つに）
    merged = []
    for cp in changepoints:
        if merged and cp["day_index"] - merged[-1]["day_index"] < window_days:
            if cp["posterior_probability"] > merged[-1]["posterior_probability"]:
                merged[-1] = cp
        else:
            merged.append(cp)

    return {
        "changepoints": merged,
        "n_events": len(events),
        "n_days": n_days,
        "mean_daily_rate": round(float(np.mean(daily)), 3),
    }


def detect_b_value_changepoints(
    b_timeseries: list[dict],
    significance: float = 0.05,
) -> list[dict]:
    """b値時系列の変化点を検出する。"""
    if len(b_timeseries) < 5:
        return []

    b_values = np.array([entry["b_value"] for entry in b_timeseries])
    changepoints = []

    for i in range(2, len(b_values) - 2):
        before = b_values[max(0, i - 3):i]
        after = b_values[i:min(len(b_values), i + 3)]

        mean_b = float(np.mean(before))
        mean_a = float(np.mean(after))
        std_b = float(np.std(before)) if len(before) > 1 else 0.1
        std_a = float(np.std(after)) if len(after) > 1 else 0.1

        # t検定的なスコア
        pooled_std = math.sqrt((std_b ** 2 + std_a ** 2) / 2) or 0.1
        t_score = abs(mean_a - mean_b) / pooled_std

        if t_score > 2.0:  # 有意な変化
            changepoints.append({
                "index": i,
                "period": b_timeseries[i].get("start", ""),
                "b_before": round(mean_b, 3),
                "b_after": round(mean_a, 3),
                "change": round(mean_a - mean_b, 3),
                "t_score": round(t_score, 2),
                "type": "increase" if mean_a > mean_b else "decrease",
            })

    return changepoints
