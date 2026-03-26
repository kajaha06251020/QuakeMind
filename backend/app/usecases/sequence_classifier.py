"""地震シーケンス自動分類。群発地震/本震-余震系列/スウォームを分類する。"""
import logging
from datetime import datetime, timezone

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def classify_sequence(events: list[EarthquakeRecord]) -> dict:
    """地震シーケンスのタイプを分類する。

    分類基準:
    - mainshock-aftershock: 最大イベントが突出（max_mag > 2番目 + 1.0）
    - swarm: マグニチュードが均一（std < 0.5、max差 < 1.0）
    - foreshock-mainshock: 活動が加速してピーク
    - unclassified: 上記に該当しない
    """
    if len(events) < 5:
        return {"type": "unclassified", "reason": "イベント数不足", "n_events": len(events)}

    mags = sorted([e.magnitude for e in events], reverse=True)
    mag_std = float(np.std(mags))
    mag_diff_top2 = mags[0] - mags[1] if len(mags) >= 2 else 0

    # 時系列の傾向
    def _ts(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    sorted_events = sorted(events, key=_ts)
    n = len(sorted_events)
    half = n // 2
    first_half_mags = [e.magnitude for e in sorted_events[:half]]
    second_half_mags = [e.magnitude for e in sorted_events[half:]]

    first_max = max(first_half_mags) if first_half_mags else 0
    second_max = max(second_half_mags) if second_half_mags else 0

    # 分類ロジック
    if mag_diff_top2 >= 1.0:
        seq_type = "mainshock_aftershock"
        confidence = min(0.95, 0.6 + mag_diff_top2 * 0.1)
        description = f"本震-余震系列。最大M{mags[0]:.1f}が突出（2番目との差: {mag_diff_top2:.1f}）"
    elif mag_std < 0.5 and mag_diff_top2 < 0.8:
        seq_type = "swarm"
        confidence = min(0.9, 0.5 + (0.5 - mag_std) * 0.5)
        description = f"群発地震（スウォーム）。マグニチュード均一（σ={mag_std:.2f}）"
    elif second_max > first_max + 0.5:
        seq_type = "foreshock_mainshock"
        confidence = 0.6
        description = f"前震-本震系列。活動が加速しM{second_max:.1f}に到達"
    else:
        seq_type = "complex"
        confidence = 0.4
        description = "複合的なシーケンス。単純な分類に当てはまらない"

    return {
        "type": seq_type,
        "confidence": round(confidence, 2),
        "description": description,
        "n_events": len(events),
        "max_magnitude": round(mags[0], 1),
        "magnitude_std": round(mag_std, 3),
        "top2_magnitude_diff": round(mag_diff_top2, 2),
    }
