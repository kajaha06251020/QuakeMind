"""因果推論エンジン。グレンジャー因果性 + 情報理論的因果推定。"""
import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


def granger_causality(x: np.ndarray, y: np.ndarray, max_lag: int = 5) -> dict:
    """グレンジャー因果性検定。xがyを予測できるかを検定する。

    H0: x は y のグレンジャー原因ではない
    """
    n = len(y)
    if n < max_lag * 3:
        return {"error": "データ不足", "causal": False}

    best_lag = 1
    best_f = 0
    best_p = 1.0

    for lag in range(1, max_lag + 1):
        if n - lag < lag + 2:
            continue

        # 制限モデル: y(t) = Σ a_i * y(t-i) + ε
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - i - 1:n - i - 1] for i in range(lag)])

        # 非制限モデル: y(t) = Σ a_i * y(t-i) + Σ b_i * x(t-i) + ε
        X_lags = np.column_stack([x[lag - i - 1:n - i - 1] for i in range(lag)])

        # OLS
        ones = np.ones((len(Y), 1))

        # 制限モデル
        Z_r = np.hstack([ones, Y_lags])
        try:
            beta_r = np.linalg.lstsq(Z_r, Y, rcond=None)[0]
            rss_r = np.sum((Y - Z_r @ beta_r) ** 2)
        except Exception:
            continue

        # 非制限モデル
        Z_u = np.hstack([ones, Y_lags, X_lags])
        try:
            beta_u = np.linalg.lstsq(Z_u, Y, rcond=None)[0]
            rss_u = np.sum((Y - Z_u @ beta_u) ** 2)
        except Exception:
            continue

        # F検定
        df1 = lag
        df2 = len(Y) - 2 * lag - 1
        if df2 <= 0 or rss_u <= 0:
            continue

        f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)
        p_value = 1 - stats.f.cdf(f_stat, df1, df2)

        if f_stat > best_f:
            best_f = f_stat
            best_p = p_value
            best_lag = lag

    return {
        "causal": best_p < 0.05,
        "f_statistic": round(float(best_f), 4),
        "p_value": round(float(best_p), 6),
        "optimal_lag": best_lag,
        "direction": "x → y",
        "significance": "significant" if best_p < 0.05 else "not_significant",
    }


def bidirectional_causality(x: np.ndarray, y: np.ndarray, max_lag: int = 5) -> dict:
    """双方向グレンジャー因果性検定。"""
    xy = granger_causality(x, y, max_lag)
    yx = granger_causality(y, x, max_lag)

    if xy.get("causal") and not yx.get("causal"):
        interpretation = "x → y (一方向因果)"
    elif not xy.get("causal") and yx.get("causal"):
        interpretation = "y → x (逆方向因果)"
    elif xy.get("causal") and yx.get("causal"):
        interpretation = "双方向因果（フィードバック）"
    else:
        interpretation = "因果関係なし"

    return {
        "x_causes_y": xy,
        "y_causes_x": yx,
        "interpretation": interpretation,
    }
