"""リアプノフ指数推定。地震時系列のカオス性を定量化し、予測可能期間を推定する。"""
import math, logging
import numpy as np

logger = logging.getLogger(__name__)


def estimate_lyapunov(timeseries: np.ndarray, embedding_dim: int = 3, tau: int = 1) -> dict:
    """最大リアプノフ指数をWolf法（簡易版）で推定する。

    λ > 0: カオス的（予測困難）
    λ ≈ 0: 臨界的
    λ < 0: 安定的（予測容易）
    """
    n = len(timeseries)
    if n < embedding_dim * tau + 20:
        return {"error": "時系列が短すぎます"}

    # 遅延座標埋め込み
    m = embedding_dim
    N = n - (m - 1) * tau
    embedded = np.array([timeseries[i:i + m * tau:tau] for i in range(N)])

    # 最近傍探索 + 発散率計算
    lyapunov_sum = 0.0
    count = 0

    for i in range(N - 1):
        # i番目の点の最近傍を探す（自分自身と時間的に近い点は除外）
        min_dist = float("inf")
        min_j = -1
        for j in range(N - 1):
            if abs(i - j) < m * tau:
                continue
            dist = np.linalg.norm(embedded[i] - embedded[j])
            if 0 < dist < min_dist:
                min_dist = dist
                min_j = j

        if min_j < 0 or min_dist == 0:
            continue

        # 1ステップ後の距離
        next_dist = np.linalg.norm(embedded[i + 1] - embedded[min_j + 1])
        if next_dist > 0 and min_dist > 0:
            lyapunov_sum += math.log(next_dist / min_dist)
            count += 1

    if count == 0:
        return {"error": "リアプノフ指数を計算できません"}

    lyapunov = lyapunov_sum / count

    # 予測可能期間の推定（e-folding time）
    if lyapunov > 0:
        prediction_horizon = 1.0 / lyapunov  # 時間単位（元のサンプリング間隔に依存）
    else:
        prediction_horizon = float("inf")

    return {
        "lyapunov_exponent": round(float(lyapunov), 6),
        "system_type": "chaotic" if lyapunov > 0.01 else "edge_of_chaos" if lyapunov > -0.01 else "stable",
        "prediction_horizon_steps": round(float(prediction_horizon), 1) if prediction_horizon != float("inf") else None,
        "embedding_dimension": m,
        "n_pairs_analyzed": count,
        "interpretation": (
            f"リアプノフ指数 λ={lyapunov:.4f}。{'カオス的: 予測は約{:.0f}ステップまで有効'.format(prediction_horizon) if lyapunov > 0.01 else '安定的: 長期予測が可能' if lyapunov < -0.01 else 'カオスの縁: 予測可能性は限定的'}"
        ),
    }
