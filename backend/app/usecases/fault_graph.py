"""時空間グラフアテンションネットワーク（簡易版）。

地震イベント間の時空間関係をグラフとしてモデル化し、
アテンション重みで断層間の相互作用を推定する。
numpy 実装（PyTorch 不要）。
"""
import math
import logging
import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0


def _build_adjacency(events: list[EarthquakeRecord], max_dist_km: float = 200.0, max_time_days: float = 30.0) -> np.ndarray:
    """時空間近接性に基づく隣接行列を構築する。"""
    n = len(events)
    adj = np.zeros((n, n))

    from datetime import datetime, timezone
    def _ts(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    times = [_ts(e) for e in events]

    for i in range(n):
        for j in range(i + 1, n):
            dlat = (events[i].latitude - events[j].latitude) * _KM_PER_DEG
            dlon = (events[i].longitude - events[j].longitude) * _KM_PER_DEG * math.cos(math.radians(events[i].latitude))
            dist_km = math.sqrt(dlat ** 2 + dlon ** 2)
            dt_days = abs(times[i] - times[j]) / 86400.0

            if dist_km <= max_dist_km and dt_days <= max_time_days:
                # 距離と時間に基づく重み（近いほど強い）
                spatial_w = 1.0 - dist_km / max_dist_km
                temporal_w = 1.0 - dt_days / max_time_days
                adj[i, j] = spatial_w * temporal_w
                adj[j, i] = adj[i, j]

    return adj


def _attention_scores(features: np.ndarray, adj: np.ndarray) -> np.ndarray:
    """簡易アテンションスコアを計算する。

    score(i,j) = softmax(features[i] · features[j]) * adj(i,j)
    """
    n = features.shape[0]
    # ドット積アテンション
    raw_scores = features @ features.T

    # 隣接行列でマスク
    masked = raw_scores * adj

    # 行方向 softmax
    attention = np.zeros_like(masked)
    for i in range(n):
        row = masked[i]
        nonzero = row != 0
        if nonzero.any():
            exp_row = np.exp(row[nonzero] - np.max(row[nonzero]))
            attention[i, nonzero] = exp_row / exp_row.sum()

    return attention


def analyze_fault_interactions(events: list[EarthquakeRecord]) -> dict:
    """地震イベント間の断層相互作用をグラフアテンションで分析する。"""
    if len(events) < 5:
        return {"error": "最低5イベント必要", "n_events": len(events)}

    n = len(events)

    # 特徴量行列: [magnitude, depth_km, lat, lon] を正規化
    features = np.array([[e.magnitude, e.depth_km, e.latitude, e.longitude] for e in events])
    # Z-score 正規化
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std == 0] = 1
    features_norm = (features - mean) / std

    # グラフ構築
    adj = _build_adjacency(events)

    # アテンション計算
    attention = _attention_scores(features_norm, adj)

    # 各イベントの「影響力スコア」= 他イベントから受けるアテンションの合計
    influence_scores = attention.sum(axis=0)

    # トップの相互作用ペア
    top_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if attention[i, j] > 0.01:
                top_pairs.append({
                    "event_i": events[i].event_id,
                    "event_j": events[j].event_id,
                    "attention_score": round(float(attention[i, j] + attention[j, i]), 4),
                    "distance_km": round(float(adj[i, j] * 200), 1),  # 近似
                })
    top_pairs.sort(key=lambda x: x["attention_score"], reverse=True)

    # 最も影響力のあるイベント
    top_indices = np.argsort(influence_scores)[::-1][:5]
    influential = [
        {"event_id": events[idx].event_id, "magnitude": events[idx].magnitude,
         "influence_score": round(float(influence_scores[idx]), 4)}
        for idx in top_indices
    ]

    return {
        "n_events": n,
        "n_edges": int(np.sum(adj > 0) // 2),
        "top_interactions": top_pairs[:10],
        "most_influential": influential,
        "graph_density": round(float(np.sum(adj > 0)) / max(n * (n - 1), 1), 4),
    }
