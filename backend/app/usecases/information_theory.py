"""情報理論的分析。地震パラメータ間の相互情報量。"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def mutual_information(x: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """離散化による相互情報量の推定。"""
    if len(x) < 10 or len(y) < 10 or len(x) != len(y):
        return 0.0

    # ヒストグラムで離散化
    hist_xy, _, _ = np.histogram2d(x, y, bins=n_bins)
    hist_x = np.sum(hist_xy, axis=1)
    hist_y = np.sum(hist_xy, axis=0)

    n = float(np.sum(hist_xy))
    if n == 0:
        return 0.0

    # 正規化
    p_xy = hist_xy / n
    p_x = hist_x / n
    p_y = hist_y / n

    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if p_xy[i, j] > 0 and p_x[i] > 0 and p_y[j] > 0:
                mi += p_xy[i, j] * np.log2(p_xy[i, j] / (p_x[i] * p_y[j]))

    return float(mi)


def analyze_parameter_dependencies(
    magnitudes: np.ndarray,
    depths: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
) -> dict:
    """地震パラメータ間の情報理論的依存性を分析する。"""
    params = {"magnitude": magnitudes, "depth": depths, "latitude": latitudes, "longitude": longitudes}
    names = list(params.keys())

    mi_matrix = {}
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            if i < j:
                mi = mutual_information(params[n1], params[n2])
                key = f"{n1}_vs_{n2}"
                mi_matrix[key] = round(mi, 4)

    # 最も依存性の高いペア
    if mi_matrix:
        max_pair = max(mi_matrix, key=mi_matrix.get)
        max_mi = mi_matrix[max_pair]
    else:
        max_pair = None
        max_mi = 0

    return {
        "mutual_information": mi_matrix,
        "strongest_dependency": {"pair": max_pair, "mi": max_mi},
        "n_samples": len(magnitudes),
        "interpretation": f"最も強い依存性: {max_pair} (MI={max_mi:.4f})" if max_pair else "分析不可",
    }
