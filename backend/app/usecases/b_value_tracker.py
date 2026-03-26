"""b値/a値の時系列追跡。スライディングウィンドウで計算。"""
import logging
from datetime import datetime, timedelta, timezone

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import analyze_gutenberg_richter

logger = logging.getLogger(__name__)
_MIN_EVENTS_PER_WINDOW = 10


def compute_b_value_timeseries(
    events: list[EarthquakeRecord],
    window_days: int = 90,
    step_days: int = 30,
) -> list[dict]:
    if len(events) < _MIN_EVENTS_PER_WINDOW:
        return []

    def _parse_ts(e: EarthquakeRecord) -> datetime:
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_events = sorted(events, key=_parse_ts)
    timestamps = [_parse_ts(e) for e in sorted_events]

    first_time = timestamps[0]
    last_time = timestamps[-1]
    window_delta = timedelta(days=window_days)
    step_delta = timedelta(days=step_days)

    results = []
    current_start = first_time

    while current_start + window_delta <= last_time:
        current_end = current_start + window_delta
        window_events = [
            e for e, t in zip(sorted_events, timestamps)
            if current_start <= t < current_end
        ]
        if len(window_events) >= _MIN_EVENTS_PER_WINDOW:
            try:
                gr = analyze_gutenberg_richter(window_events)
                results.append({
                    "start": current_start.date().isoformat(),
                    "end": current_end.date().isoformat(),
                    "b_value": gr.b_value,
                    "b_uncertainty": gr.b_uncertainty,
                    "a_value": gr.a_value,
                    "mc": gr.mc,
                    "n_events": gr.n_events,
                })
            except (ValueError, Exception) as e:
                logger.debug("[BValueTracker] ウィンドウ %s-%s スキップ: %s",
                            current_start.date(), current_end.date(), e)
        current_start += step_delta

    return results
