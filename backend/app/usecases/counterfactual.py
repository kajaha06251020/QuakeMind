"""反事実分析。「もしこの地震が起きていなかったら」をシミュレーション。"""
import logging
from datetime import datetime, timezone

import numpy as np

from app.domain.seismology import EarthquakeRecord
from app.usecases.etas import etas_forecast

logger = logging.getLogger(__name__)


def counterfactual_analysis(
    events: list[EarthquakeRecord],
    removed_event_id: str,
    forecast_hours: int = 72,
) -> dict:
    """特定のイベントがなかった場合の反事実シナリオを生成する。"""
    target = next((e for e in events if e.event_id == removed_event_id), None)
    if target is None:
        return {"error": f"イベント {removed_event_id} が見つかりません"}

    # 実際のシナリオ
    actual = etas_forecast(events, forecast_hours=forecast_hours)

    # 反事実シナリオ（対象イベントを除外）
    counterfactual_events = [e for e in events if e.event_id != removed_event_id]
    counterfactual = etas_forecast(counterfactual_events, forecast_hours=forecast_hours)

    # 差分分析
    actual_expected = actual.get("expected_events", 0)
    cf_expected = counterfactual.get("expected_events", 0)
    impact = actual_expected - cf_expected

    return {
        "removed_event": {
            "event_id": removed_event_id,
            "magnitude": target.magnitude,
            "latitude": target.latitude,
            "longitude": target.longitude,
        },
        "actual_scenario": {
            "expected_events_next_72h": actual_expected,
            "probability_m4_plus": actual.get("probability_m4_plus", 0),
        },
        "counterfactual_scenario": {
            "expected_events_next_72h": cf_expected,
            "probability_m4_plus": counterfactual.get("probability_m4_plus", 0),
        },
        "impact": {
            "additional_events_caused": round(impact, 2),
            "impact_percentage": round(impact / max(cf_expected, 0.01) * 100, 1),
            "interpretation": (
                f"M{target.magnitude}の地震は追加で{impact:.1f}件の地震を誘発する効果がある"
                if impact > 0.1 else
                "この地震の除去による影響は限定的"
            ),
        },
    }
