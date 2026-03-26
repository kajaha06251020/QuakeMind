"""最大エントロピーモデル。観測制約のみから最もバイアスのない予測を導出する。"""
import logging
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def max_entropy_rate(observed_mean: float, observed_var: float, n_bins: int = 20, max_count: int = 30) -> dict:
    counts = np.arange(max_count + 1)

    def neg_entropy(lambdas):
        l1, l2 = lambdas
        log_Z = np.log(np.sum(np.exp(-l1 * counts - l2 * counts ** 2)))
        p = np.exp(-l1 * counts - l2 * counts ** 2 - log_Z)
        mean_c = np.sum(p * counts)
        var_c = np.sum(p * counts ** 2) - mean_c ** 2
        constraint_violation = (mean_c - observed_mean) ** 2 + (var_c - observed_var) ** 2
        entropy = -np.sum(p * np.log(np.clip(p, 1e-10, None)))
        return -entropy + 100 * constraint_violation

    result = minimize(neg_entropy, [0.1, 0.01], method="Nelder-Mead", options={"maxiter": 500})
    l1, l2 = result.x
    log_Z = np.log(np.sum(np.exp(-l1 * counts - l2 * counts ** 2)))
    p = np.exp(-l1 * counts - l2 * counts ** 2 - log_Z)

    entropy = -float(np.sum(p * np.log(np.clip(p, 1e-10, None))))
    model_mean = float(np.sum(p * counts))
    model_var = float(np.sum(p * counts ** 2) - model_mean ** 2)

    return {
        "distribution": {int(k): round(float(v), 6) for k, v in zip(counts[:15], p[:15]) if v > 0.001},
        "entropy": round(entropy, 4),
        "model_mean": round(model_mean, 2),
        "model_variance": round(model_var, 2),
        "observed_mean": round(observed_mean, 2),
        "observed_variance": round(observed_var, 2),
        "lagrange_multipliers": {"lambda1": round(float(l1), 4), "lambda2": round(float(l2), 4)},
    }
