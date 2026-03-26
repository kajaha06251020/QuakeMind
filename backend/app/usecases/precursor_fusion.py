"""マルチドメイン前兆融合。複数の弱いシグナルを1つの統合前兆スコアに融合する。"""
import math
import logging

logger = logging.getLogger(__name__)


def compute_precursor_score(signals: dict) -> dict:
    """複数の前兆シグナルを統合スコアに融合する。

    Args:
        signals: {
            "b_value_drop": float (0-1, 低下の大きさ),
            "anomaly_p_value": float (0-1, 小さいほど異常),
            "quiescence_ratio": float (0-1, 小さいほど静穏),
            "cluster_density": float (0-1, 高いほど集中),
            "coulomb_stress": float (MPa, 正が促進),
            "geomagnetic_deviation": float (0-1),
            "gnss_displacement": float (0-1),
        }
    """
    # 各シグナルの前兆強度 (0-1) に変換
    indicators = {}

    b_drop = signals.get("b_value_drop", 0)
    indicators["b_value"] = min(1.0, max(0, b_drop / 0.5))

    p_val = signals.get("anomaly_p_value", 1.0)
    indicators["anomaly"] = min(1.0, max(0, 1 - p_val / 0.05)) if p_val < 0.05 else 0

    q_ratio = signals.get("quiescence_ratio", 1.0)
    indicators["quiescence"] = min(1.0, max(0, 1 - q_ratio / 0.5)) if q_ratio < 0.5 else 0

    c_density = signals.get("cluster_density", 0)
    indicators["clustering"] = min(1.0, c_density)

    cfs = signals.get("coulomb_stress", 0)
    indicators["coulomb"] = min(1.0, max(0, cfs / 0.1)) if cfs > 0 else 0

    geo = signals.get("geomagnetic_deviation", 0)
    indicators["geomagnetic"] = min(1.0, geo)

    gnss = signals.get("gnss_displacement", 0)
    indicators["gnss"] = min(1.0, gnss)

    # 重み付き融合（地震学的根拠の強さで重み付け）
    weights = {
        "b_value": 3.0,      # 強い根拠
        "anomaly": 2.5,      # 統計的に有意
        "quiescence": 2.0,   # 中程度の根拠
        "clustering": 1.5,   # 観察的
        "coulomb": 3.0,      # 物理モデルベース
        "geomagnetic": 0.5,  # 研究段階
        "gnss": 1.0,         # 中程度の根拠
    }

    total_weight = sum(weights.values())
    weighted_sum = sum(indicators[k] * weights[k] for k in indicators)
    integrated_score = weighted_sum / total_weight

    # 複数シグナルの同時検出ボーナス
    active_signals = sum(1 for v in indicators.values() if v > 0.3)
    if active_signals >= 3:
        synergy_bonus = 0.1 * (active_signals - 2)
        integrated_score = min(1.0, integrated_score + synergy_bonus)

    # リスクレベル
    if integrated_score >= 0.7:
        level = "critical"
    elif integrated_score >= 0.5:
        level = "high"
    elif integrated_score >= 0.3:
        level = "elevated"
    elif integrated_score >= 0.1:
        level = "advisory"
    else:
        level = "normal"

    return {
        "integrated_score": round(integrated_score, 4),
        "risk_level": level,
        "active_signals": active_signals,
        "signal_indicators": {k: round(v, 4) for k, v in indicators.items()},
        "weights_used": weights,
    }
