"""確率的破壊伝播シミュレーション。モンテカルロ法で断層破壊の広がりを予測する。"""
import math
import logging
import numpy as np
from app.usecases.finite_fault import estimate_fault_geometry

logger = logging.getLogger(__name__)

_FAULT_SEGMENTS = [
    {"id": "nankai_west", "name": "南海（西）", "lat": 32.5, "lon": 134.0, "length_km": 200, "connected_to": ["nankai_east"]},
    {"id": "nankai_east", "name": "南海（東）", "lat": 33.5, "lon": 136.0, "length_km": 200, "connected_to": ["nankai_west", "tokai"]},
    {"id": "tokai", "name": "東海", "lat": 34.5, "lon": 138.0, "length_km": 200, "connected_to": ["nankai_east", "sagami"]},
    {"id": "sagami", "name": "相模", "lat": 35.0, "lon": 139.5, "length_km": 150, "connected_to": ["tokai"]},
    {"id": "japan_trench_s", "name": "日本海溝（南部）", "lat": 37.0, "lon": 142.0, "length_km": 300, "connected_to": ["japan_trench_n"]},
    {"id": "japan_trench_n", "name": "日本海溝（北部）", "lat": 40.0, "lon": 143.0, "length_km": 300, "connected_to": ["japan_trench_s"]},
]


def simulate_rupture(
    initial_segment_id: str,
    initial_magnitude: float,
    n_simulations: int = 1000,
    propagation_probability: float = 0.3,
) -> dict:
    segments = {s["id"]: s for s in _FAULT_SEGMENTS}
    if initial_segment_id not in segments:
        return {"error": f"セグメント {initial_segment_id} が見つかりません", "available": list(segments.keys())}

    rng = np.random.default_rng(42)
    results = []

    for _ in range(n_simulations):
        ruptured = {initial_segment_id}
        queue = [initial_segment_id]
        total_length = segments[initial_segment_id]["length_km"]

        while queue:
            current = queue.pop(0)
            for neighbor_id in segments[current].get("connected_to", []):
                if neighbor_id not in ruptured and neighbor_id in segments:
                    # 伝播確率: 基本確率 * マグニチュード補正
                    p = propagation_probability * (initial_magnitude / 7.0)
                    p = min(0.95, p)
                    if rng.random() < p:
                        ruptured.add(neighbor_id)
                        queue.append(neighbor_id)
                        total_length += segments[neighbor_id]["length_km"]

        # 破壊長から等価マグニチュードを推定: M = (log10(L) + 2.44) / 0.59
        eq_mag = (math.log10(max(total_length, 1)) + 2.44) / 0.59
        results.append({"ruptured": list(ruptured), "total_length_km": total_length, "equivalent_magnitude": round(eq_mag, 1)})

    # 統計
    lengths = [r["total_length_km"] for r in results]
    magnitudes = [r["equivalent_magnitude"] for r in results]

    # 各セグメントの破壊確率
    seg_probs = {}
    for seg_id in segments:
        count = sum(1 for r in results if seg_id in r["ruptured"])
        seg_probs[seg_id] = {"name": segments[seg_id]["name"], "probability": round(count / n_simulations, 4)}

    return {
        "initial_segment": initial_segment_id,
        "initial_magnitude": initial_magnitude,
        "n_simulations": n_simulations,
        "rupture_length": {"mean_km": round(float(np.mean(lengths)), 1), "max_km": round(float(np.max(lengths)), 1), "p95_km": round(float(np.percentile(lengths, 95)), 1)},
        "equivalent_magnitude": {"mean": round(float(np.mean(magnitudes)), 1), "max": round(float(np.max(magnitudes)), 1), "p95": round(float(np.percentile(magnitudes, 95)), 1)},
        "segment_rupture_probabilities": seg_probs,
    }
