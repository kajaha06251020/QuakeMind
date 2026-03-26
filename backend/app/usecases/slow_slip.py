"""スロースリップ検出と通常地震との相関分析。"""
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def detect_slow_slip_correlation(
    events: list[EarthquakeRecord],
    displacement_data: list[dict] | None = None,
) -> dict:
    """スロースリップイベントと通常地震の時間的相関を分析する。

    displacement_data がない場合は、地震活動パターンからスロースリップの間接的兆候を検出する。
    兆候: 一時的な地震活動低下→急増パターン（スロースリップ中は静穏化、後に活発化）
    """
    if len(events) < 20:
        return {"error": "最低20イベント必要"}

    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except: return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_e = sorted(events, key=_ts)
    timestamps = [_ts(e) for e in sorted_e]

    # 日別カウント
    from collections import Counter
    first = timestamps[0].date()
    last = timestamps[-1].date()
    n_days = (last - first).days + 1
    if n_days < 30:
        return {"error": "期間が短すぎます（最低30日必要）"}

    daily = Counter(t.date() for t in timestamps)
    counts = np.array([daily.get(first + timedelta(days=d), 0) for d in range(n_days)], dtype=float)

    # スロースリップ候補の検出: 静穏期間(7日以上の低活動)→活発期間
    mean_rate = np.mean(counts)
    quiet_threshold = mean_rate * 0.3
    active_threshold = mean_rate * 2.0

    candidates = []
    i = 0
    while i < n_days - 14:
        window = counts[i:i+7]
        if np.mean(window) <= quiet_threshold:
            # 静穏期間を検出、次の活発期間を探す
            j = i + 7
            while j < min(i + 21, n_days):
                if counts[j] >= active_threshold:
                    candidates.append({
                        "quiet_start": (first + timedelta(days=i)).isoformat(),
                        "quiet_end": (first + timedelta(days=i+7)).isoformat(),
                        "active_day": (first + timedelta(days=j)).isoformat(),
                        "quiet_rate": round(float(np.mean(window)), 2),
                        "active_rate": round(float(counts[j]), 1),
                        "pattern": "quiet_then_active",
                    })
                    break
                j += 1
            i = j + 1
        else:
            i += 1

    # GNSS変位データとの相関（提供された場合）
    gnss_correlation = None
    if displacement_data and len(displacement_data) >= 10:
        displacements = np.array([d.get("displacement_mm", 0) for d in displacement_data])
        if len(displacements) == n_days:
            corr = float(np.corrcoef(counts, displacements)[0, 1])
            gnss_correlation = {"correlation": round(corr, 4), "n_points": len(displacements)}

    return {
        "n_events": len(events),
        "observation_days": n_days,
        "mean_daily_rate": round(float(mean_rate), 2),
        "slow_slip_candidates": candidates,
        "n_candidates": len(candidates),
        "gnss_correlation": gnss_correlation,
        "interpretation": (
            f"{len(candidates)}個のスロースリップ候補パターン（静穏化→活発化）を検出。"
            if candidates else "明確なスロースリップ兆候は検出されなかった。"
        ),
    }
