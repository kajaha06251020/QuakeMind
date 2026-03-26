"""断層治癒率推定。過去の再来間隔から治癒速度を推定する。"""
import math, logging
import numpy as np

logger = logging.getLogger(__name__)

_HISTORICAL_SEQUENCES = [
    {"fault": "南海トラフ", "events": [1707, 1854, 1946], "magnitudes": [8.6, 8.4, 8.0]},
    {"fault": "日本海溝（三陸沖）", "events": [1896, 1933, 2011], "magnitudes": [8.2, 8.1, 9.0]},
    {"fault": "相模トラフ", "events": [1703, 1923], "magnitudes": [8.2, 7.9]},
    {"fault": "十勝沖", "events": [1952, 2003], "magnitudes": [8.2, 8.0]},
]


def estimate_healing_rate(fault_name: str | None = None) -> dict:
    """断層の治癒率を推定する。"""
    results = []

    targets = _HISTORICAL_SEQUENCES
    if fault_name:
        targets = [s for s in targets if fault_name in s["fault"]]

    for seq in targets:
        events = seq["events"]
        if len(events) < 2:
            continue

        intervals = [events[i+1] - events[i] for i in range(len(events)-1)]
        mean_interval = np.mean(intervals)

        # 治癒率: 1/再来間隔 (1/年)
        healing_rate = 1.0 / mean_interval if mean_interval > 0 else 0

        # マグニチュードのトレンド
        mag_trend = (seq["magnitudes"][-1] - seq["magnitudes"][0]) / max(len(seq["magnitudes"]) - 1, 1)

        # 次の地震までの推定残り時間
        last_event = events[-1]
        elapsed = 2026 - last_event
        remaining = max(0, mean_interval - elapsed)
        completeness = min(1.0, elapsed / mean_interval)

        results.append({
            "fault": seq["fault"],
            "historical_events": events,
            "magnitudes": seq["magnitudes"],
            "mean_recurrence_years": round(float(mean_interval), 1),
            "healing_rate_per_year": round(float(healing_rate), 6),
            "elapsed_since_last_years": elapsed,
            "estimated_remaining_years": round(float(remaining), 0),
            "cycle_completeness": round(float(completeness), 3),
            "magnitude_trend": round(float(mag_trend), 2),
        })

    return {"faults": results, "n_analyzed": len(results)}
