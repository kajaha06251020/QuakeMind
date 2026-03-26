"""地域別リスクプロファイル。過去の統計 + 活断層情報を統合。"""
import logging

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

# 主要活断層帯（地震調査研究推進本部データに基づく概要）
_ACTIVE_FAULTS = {
    "東京都": [
        {"name": "立川断層帯", "max_magnitude": 7.4, "probability_30yr": 0.02},
    ],
    "大阪府": [
        {"name": "上町断層帯", "max_magnitude": 7.5, "probability_30yr": 0.03},
    ],
    "宮城県": [
        {"name": "長町-利府線断層帯", "max_magnitude": 7.5, "probability_30yr": 0.01},
    ],
    "静岡県": [
        {"name": "富士川河口断層帯", "max_magnitude": 8.0, "probability_30yr": 0.10},
    ],
    "愛知県": [
        {"name": "猿投-高浜断層帯", "max_magnitude": 7.3, "probability_30yr": 0.01},
    ],
}


def compute_risk_profile(region: str, events: list[EarthquakeRecord]) -> dict:
    """地域の総合リスクプロファイルを計算する。"""
    faults = _ACTIVE_FAULTS.get(region, [])

    # 過去データからの統計
    if events:
        mags = [e.magnitude for e in events]
        historical = {
            "total_events": len(events),
            "max_magnitude": round(max(mags), 1),
            "avg_magnitude": round(sum(mags) / len(mags), 2),
            "events_m5_plus": sum(1 for m in mags if m >= 5.0),
            "events_m6_plus": sum(1 for m in mags if m >= 6.0),
        }
    else:
        historical = {"total_events": 0, "max_magnitude": 0, "avg_magnitude": 0, "events_m5_plus": 0, "events_m6_plus": 0}

    # 総合リスクスコア（0-100）
    fault_risk = max((f["probability_30yr"] for f in faults), default=0) * 100
    historical_risk = min(historical["events_m5_plus"] * 5, 50)
    total_score = min(100, fault_risk + historical_risk)

    if total_score >= 60:
        risk_level = "very_high"
    elif total_score >= 40:
        risk_level = "high"
    elif total_score >= 20:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "region": region,
        "risk_score": round(total_score, 1),
        "risk_level": risk_level,
        "active_faults": faults,
        "historical_statistics": historical,
    }
