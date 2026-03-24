"""Predict Agent: 地震リスクスコアを計算する（ルールベース、PINN は Phase 2 で差し替え）。"""
import logging
import math

from state import EventState, compute_severity

logger = logging.getLogger(__name__)


def _estimate_intensity(magnitude: float, depth_km: float, distance_km: float = 100.0) -> float:
    """震度推定（距離減衰式）。
    I = 2.68 + 1.72*M - 1.58*log10(R)  R: 震源距離(km)
    震源距離 = sqrt(distance_km^2 + depth_km^2)
    """
    hypo_dist = math.sqrt(distance_km**2 + depth_km**2)
    if hypo_dist <= 0:
        hypo_dist = 1.0
    intensity = 2.68 + 1.72 * magnitude - 1.58 * math.log10(hypo_dist)
    return max(0.0, min(7.0, round(intensity, 2)))


def _estimate_aftershock_prob(magnitude: float, depth_km: float) -> float:
    """72時間以内の M5.0 以上余震確率（大森・宇津則近似）。
    K=0.04, c=0.02, p=1.1 で 0〜72 時間を数値積分（台形法）。
    規模と深さで K をスケール。
    """
    K = 0.04 * max(0.1, magnitude - 3.0)
    c = 0.02
    p = 1.1

    # 台形法で累積余震数 N(72h) を算出
    dt = 1.0  # 1時間刻み
    total = 0.0
    for t in range(0, 72):
        total += K / ((t + c) ** p) * dt

    # 規模が大きいほど確率が上がるよう正規化（上限 0.95）
    prob = 1.0 - math.exp(-total)
    return round(min(0.95, prob), 3)


def _check_tsunami_risk(magnitude: float, depth_km: float) -> bool:
    """津波リスクフラグ: M6.5 以上かつ深度 60km 未満。"""
    return magnitude >= 6.5 and depth_km < 60.0


async def predict_node(state: EventState) -> dict:
    """LangGraph ノード: リスクスコアを算出して state を更新する。"""
    try:
        magnitude = state["magnitude"]
        depth_km = state["depth_km"]

        estimated_intensity = _estimate_intensity(magnitude, depth_km)
        aftershock_prob_72h = _estimate_aftershock_prob(magnitude, depth_km)
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
