"""統一確率フレームワーク。全分析結果をベイズネットワークで統合する。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)


class BayesianEarthquakeNetwork:
    """地震予測のためのベイズネットワーク。

    ノード:
    - b_value_anomaly: b値の異常度 (0-1)
    - rate_anomaly: 発生率の異常度 (0-1)
    - stress_loading: 応力蓄積度 (0-1)
    - clustering_intensity: クラスタリング強度 (0-1)
    - quiescence: 静穏化度 (0-1)
    - criticality: 臨界度 (0-1)
    → large_earthquake_probability: 大地震確率 (0-1)

    因果構造:
    stress_loading → b_value_anomaly → large_eq
    stress_loading → rate_anomaly → large_eq
    stress_loading → quiescence → large_eq
    clustering_intensity → large_eq
    criticality → large_eq
    """

    # 条件付き確率テーブル（専門家知識 + 文献ベース）
    _CPT_WEIGHTS = {
        "b_value_anomaly": 0.25,
        "rate_anomaly": 0.20,
        "stress_loading": 0.20,
        "clustering_intensity": 0.10,
        "quiescence": 0.10,
        "criticality": 0.15,
    }

    # 因果的相互作用（ノード間の増幅係数）
    _INTERACTIONS = [
        ("stress_loading", "b_value_anomaly", 0.3),  # 応力→b値
        ("stress_loading", "rate_anomaly", 0.2),      # 応力→発生率
        ("b_value_anomaly", "quiescence", 0.15),      # b値→静穏化
        ("clustering_intensity", "rate_anomaly", 0.1), # クラスタ→発生率
    ]

    def __init__(self):
        self.evidence: dict[str, float] = {}
        self.posterior: dict[str, float] = {}

    def set_evidence(self, **kwargs) -> None:
        """観測値（エビデンス）を設定する。各値は0-1。"""
        for k, v in kwargs.items():
            self.evidence[k] = max(0.0, min(1.0, float(v)))

    def infer(self) -> dict:
        """ベイズ推論を実行する。"""
        nodes = dict(self.evidence)

        # 因果的相互作用の伝播
        for source, target, strength in self._INTERACTIONS:
            if source in nodes and target in nodes:
                boost = nodes[source] * strength
                nodes[target] = min(1.0, nodes[target] + boost)
            elif source in nodes and target not in nodes:
                nodes[target] = nodes[source] * strength

        # 大地震確率の計算（重み付き結合 + シグモイド）
        weighted_sum = 0.0
        total_weight = 0.0
        active_signals = 0

        for node, weight in self._CPT_WEIGHTS.items():
            value = nodes.get(node, 0.0)
            weighted_sum += value * weight
            total_weight += weight
            if value > 0.3:
                active_signals += 1

        base_prob = weighted_sum / max(total_weight, 0.01)

        # 複数シグナル同時検出ボーナス（非線形増幅）
        if active_signals >= 4:
            synergy = 0.15 * (active_signals - 3)
            base_prob = min(1.0, base_prob + synergy)

        # シグモイド変換で極端な値を抑制
        logit = math.log(max(base_prob, 0.001) / max(1 - base_prob, 0.001))
        probability = 1 / (1 + math.exp(-logit))

        self.posterior = {
            "large_earthquake_probability": round(probability, 4),
            "node_values": {k: round(v, 4) for k, v in nodes.items()},
            "active_signals": active_signals,
            "evidence_used": list(self.evidence.keys()),
        }

        return self.posterior

    def explain(self) -> list[dict]:
        """推論の因果的説明を生成する。"""
        if not self.posterior:
            return []

        explanations = []
        nodes = self.posterior.get("node_values", {})

        for node, value in sorted(nodes.items(), key=lambda x: x[1], reverse=True):
            if value > 0.3 and node in self._CPT_WEIGHTS:
                weight = self._CPT_WEIGHTS[node]
                contribution = round(value * weight, 4)
                explanations.append({
                    "factor": node,
                    "value": round(value, 4),
                    "weight": weight,
                    "contribution": contribution,
                    "description": _NODE_DESCRIPTIONS.get(node, ""),
                })

        return explanations


_NODE_DESCRIPTIONS = {
    "b_value_anomaly": "b値の異常な低下。応力集中の兆候。",
    "rate_anomaly": "地震発生率の統計的に有意な変化。",
    "stress_loading": "クーロン応力の蓄積。断層への力の集中。",
    "clustering_intensity": "地震の空間的集中。群発地震の可能性。",
    "quiescence": "地震活動の異常な低下。断層ロッキングの可能性。",
    "criticality": "地殻の臨界状態への接近。",
}


def unified_probability(analysis_results: dict) -> dict:
    """全分析結果から統一された地震発生確率を計算する。"""
    net = BayesianEarthquakeNetwork()

    # 各分析結果をエビデンスに変換
    evidence = {}

    if "b_value_change" in analysis_results:
        evidence["b_value_anomaly"] = min(1.0, max(0, abs(analysis_results["b_value_change"]) / 0.5))

    if "anomaly_detected" in analysis_results:
        p = analysis_results.get("p_value", 1.0)
        evidence["rate_anomaly"] = min(1.0, max(0, 1 - p / 0.05)) if p < 0.05 else 0

    if "cumulative_stress_mpa" in analysis_results:
        evidence["stress_loading"] = min(1.0, max(0, analysis_results["cumulative_stress_mpa"] / 0.1))

    if "n_clusters" in analysis_results:
        evidence["clustering_intensity"] = min(1.0, analysis_results["n_clusters"] / 5)

    if "is_quiescent" in analysis_results:
        evidence["quiescence"] = 0.8 if analysis_results["is_quiescent"] else 0.0

    if "criticality_index" in analysis_results:
        evidence["criticality"] = min(1.0, analysis_results["criticality_index"])

    net.set_evidence(**evidence)
    result = net.infer()
    explanations = net.explain()

    prob = result["large_earthquake_probability"]
    if prob >= 0.6:
        risk_level = "critical"
    elif prob >= 0.4:
        risk_level = "high"
    elif prob >= 0.2:
        risk_level = "elevated"
    else:
        risk_level = "normal"

    return {
        "unified_probability": prob,
        "risk_level": risk_level,
        "bayesian_network": result,
        "causal_explanation": explanations,
        "n_evidence_sources": len(evidence),
    }
