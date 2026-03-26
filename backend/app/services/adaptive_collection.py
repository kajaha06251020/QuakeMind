"""適応的データ収集戦略。リスクに応じてデータ取得頻度を自動調整する。"""
import logging

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 60  # 秒
_MIN_INTERVAL = 10
_MAX_INTERVAL = 300

_current_intervals: dict[str, int] = {}


def compute_adaptive_intervals(risk_level: str, source_priorities: dict[str, float] | None = None) -> dict[str, int]:
    """リスクレベルに応じた適応的ポーリング間隔を計算する。"""
    multipliers = {"critical": 0.15, "high": 0.3, "elevated": 0.6, "normal": 1.0}
    mult = multipliers.get(risk_level, 1.0)

    sources = source_priorities or {"p2p": 1.0, "usgs": 0.8, "emsc": 0.6, "iris": 0.5, "jma_intensity": 0.9, "tsunami_obs": 0.9}

    intervals = {}
    for source, priority in sources.items():
        base = _DEFAULT_INTERVAL / max(priority, 0.1)
        adjusted = int(base * mult)
        intervals[source] = max(_MIN_INTERVAL, min(_MAX_INTERVAL, adjusted))

    return intervals


def get_current_intervals() -> dict[str, int]:
    return _current_intervals.copy() if _current_intervals else compute_adaptive_intervals("normal")


def update_intervals(risk_level: str) -> dict[str, int]:
    global _current_intervals
    _current_intervals = compute_adaptive_intervals(risk_level)
    logger.info("[Adaptive] リスク=%s、間隔を更新: %s", risk_level, _current_intervals)
    return _current_intervals
