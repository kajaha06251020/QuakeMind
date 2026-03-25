"""Predict Agent: 地震リスクスコアを計算する（ルールベース、PINN は Phase 2 で差し替え）。"""
import logging
import math

from app.domain.models import EventState, compute_severity

logger = logging.getLogger(__name__)


def _estimate_intensity(magnitude: float, depth_km: float, distance_km: float = 100.0) -> float:
    hypo_dist = math.sqrt(distance_km**2 + depth_km**2)
    if hypo_dist <= 0:
        hypo_dist = 1.0
    intensity = 2.68 + 1.0 * magnitude - 1.58 * math.log10(hypo_dist)
    return max(0.0, min(7.0, round(intensity, 2)))


def _estimate_aftershock_prob(magnitude: float) -> float:
    """マグニチュード級の余震が72時間以内に発生する確率（経験式）。
    Bath則に基づく近似: 大きい本震ほど余震確率が高い。
    """
    if magnitude <= 3.0:
        return 0.0
    prob = 1.0 - math.exp(-0.6 * (magnitude - 3.0))
    return round(min(0.95, max(0.0, prob)), 3)


def _check_tsunami_risk(magnitude: float, depth_km: float) -> bool:
    return magnitude >= 6.5 and depth_km < 60.0


async def predict_node(state: EventState) -> dict:
    try:
        magnitude = state["magnitude"]
        depth_km = state["depth_km"]
        estimated_intensity = _estimate_intensity(magnitude, depth_km)
        aftershock_prob_72h = _estimate_aftershock_prob(magnitude)
        tsunami_flag = _check_tsunami_risk(magnitude, depth_km)
        severity = compute_severity(estimated_intensity, aftershock_prob_72h, tsunami_flag)
        logger.info(
            "[Predict] %s M%.1f 推定震度=%.2f 余震確率=%.3f 津波=%s severity=%s",
            state["event_id"], magnitude, estimated_intensity,
            aftershock_prob_72h, tsunami_flag, severity,
        )
        return {
            "estimated_intensity": estimated_intensity,
            "aftershock_prob_72h": aftershock_prob_72h,
            "tsunami_flag": tsunami_flag,
            "severity": severity,
            "error": "",
        }
    except Exception as e:
        logger.error("[Predict] エラー: %s", e)
        return {"error": f"predict: {e}"}
