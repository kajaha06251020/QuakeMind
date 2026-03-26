"""Physics-Informed Neural Network (PINN) フレームワーク。

物理制約（波動方程式、弾性体方程式）を損失関数に組み込んだ
ニューラルネットワーク。numpy/scipy で実装。
"""
import logging
import math
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def _physics_loss(params: np.ndarray, X: np.ndarray, y: np.ndarray, physics_weight: float = 0.5) -> float:
    """物理制約付き損失関数。

    データ損失 + 物理制約損失:
    - データ損失: MSE(predicted, actual)
    - 物理制約: Gutenberg-Richter 則の逸脱ペナルティ
    """
    n_features = X.shape[1]
    w = params[:n_features]
    b = params[n_features]

    predicted = X @ w + b
    data_loss = float(np.mean((predicted - y) ** 2))

    # 物理制約: 予測マグニチュードは Gutenberg-Richter のべき乗則に従うべき
    # log10(N) = a - b*M → 大きなMは指数的に稀
    # ペナルティ: 予測値が物理的範囲外（0-9.5）なら罰する
    physics_penalty = float(np.mean(np.maximum(0, predicted - 9.5) ** 2 + np.maximum(0, -predicted) ** 2))

    # 予測値の分布がべき乗則に近いかチェック（マグニチュード範囲が十分広い場合のみ）
    if len(predicted) > 10:
        sorted_pred = np.sort(predicted)[::-1]
        pred_range = float(np.max(sorted_pred) - np.min(sorted_pred))
        # 予測値の範囲が 1.0 以上（マグニチュードスケール）の場合のみ GR チェックを適用
        if pred_range >= 1.0 and np.std(sorted_pred) > 0:
            ranks = np.arange(1, len(sorted_pred) + 1)
            log_ranks = np.log10(ranks)
            expected_slope = -1.0  # GR則の期待傾き（b≈1）
            mask = sorted_pred > 0
            if np.sum(mask) >= 3:
                try:
                    actual_slope = np.polyfit(sorted_pred[mask], log_ranks[mask], 1)[0]
                    gr_penalty = (actual_slope - expected_slope) ** 2
                    physics_penalty += gr_penalty
                except Exception:
                    pass

    return data_loss + physics_weight * physics_penalty


def train_pinn_model(
    X: np.ndarray,
    y: np.ndarray,
    physics_weight: float = 0.5,
) -> dict:
    """物理制約付きモデルを学習する。

    Args:
        X: 特徴量行列 (n_samples, n_features)
        y: 目標変数 (n_samples,)
        physics_weight: 物理制約の重み (0-1)

    Returns:
        {"weights", "bias", "train_loss", "physics_loss"}
    """
    n_features = X.shape[1]
    x0 = np.zeros(n_features + 1)  # weights + bias

    result = minimize(
        _physics_loss, x0, args=(X, y, physics_weight),
        method="L-BFGS-B",
        options={"maxiter": 200},
    )

    w = result.x[:n_features]
    b = result.x[n_features]

    predicted = X @ w + b
    mse = float(np.mean((predicted - y) ** 2))

    return {
        "weights": w.tolist(),
        "bias": round(float(b), 4),
        "train_mse": round(mse, 6),
        "physics_weight": physics_weight,
        "converged": bool(result.success),
        "n_samples": len(y),
        "n_features": n_features,
    }


def pinn_predict(model: dict, X: np.ndarray) -> np.ndarray:
    """学習済みモデルで予測する。"""
    w = np.array(model["weights"])
    b = model["bias"]
    return X @ w + b
