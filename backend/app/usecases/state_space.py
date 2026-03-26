"""ベイズ状態空間モデル。隠れた応力状態をカルマンフィルタで推定する。"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def kalman_stress_filter(observations: list[float], process_noise: float = 0.01, obs_noise: float = 0.1) -> dict:
    if len(observations) < 5:
        return {"error": "最低5観測点必要"}

    n = len(observations)
    state = np.zeros(n)   # 推定応力
    cov = np.zeros(n)     # 推定共分散

    state[0] = observations[0]
    cov[0] = 1.0

    for t in range(1, n):
        # 予測
        state_pred = state[t - 1]
        cov_pred = cov[t - 1] + process_noise
        # 更新
        K = cov_pred / (cov_pred + obs_noise)
        state[t] = state_pred + K * (observations[t] - state_pred)
        cov[t] = (1 - K) * cov_pred

    # トレンド検出
    if n >= 10:
        recent = state[-5:]
        trend = float(np.polyfit(range(5), recent, 1)[0])
    else:
        trend = 0.0

    return {
        "estimated_states": [round(float(s), 4) for s in state],
        "uncertainties": [round(float(c ** 0.5), 4) for c in cov],
        "current_state": round(float(state[-1]), 4),
        "current_uncertainty": round(float(cov[-1] ** 0.5), 4),
        "trend": round(trend, 4),
        "trend_direction": "increasing" if trend > 0.01 else "decreasing" if trend < -0.01 else "stable",
    }
