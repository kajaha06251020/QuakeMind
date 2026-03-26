"""創発パターン検出。教師なし学習で未知の前兆パターンを発見する。"""
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def detect_emergent_patterns(events: list[EarthquakeRecord], n_clusters: int = 5) -> dict:
    if len(events) < 20:
        return {"error": "最低20イベント必要"}

    features = np.array([[e.magnitude, e.depth_km, e.latitude, e.longitude] for e in events])
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std == 0] = 1
    X = (features - mean) / std

    # K-means (手動実装)
    rng = np.random.default_rng(42)
    n = len(X)
    k = min(n_clusters, n // 5)
    centers = X[rng.choice(n, k, replace=False)]

    for _ in range(20):
        dists = np.array([[np.sum((x - c) ** 2) for c in centers] for x in X])
        labels = np.argmin(dists, axis=1)
        new_centers = np.array([
            X[labels == i].mean(axis=0) if np.sum(labels == i) > 0 else centers[i]
            for i in range(k)
        ])
        if np.allclose(centers, new_centers):
            break
        centers = new_centers

    # 各クラスタの異常度（中心からの平均距離）
    patterns = []
    for i in range(k):
        mask = labels == i
        if not mask.any():
            continue
        cluster_features = X[mask]
        intra_dist = float(np.mean(np.sum((cluster_features - centers[i]) ** 2, axis=1) ** 0.5))

        # 他クラスタとの分離度
        inter_dists = [
            float(np.sum((centers[i] - centers[j]) ** 2) ** 0.5)
            for j in range(k) if j != i
        ]
        separation = float(np.mean(inter_dists)) if inter_dists else 0

        novelty = separation / max(intra_dist, 0.01)

        patterns.append({
            "cluster_id": i,
            "n_events": int(mask.sum()),
            "center_magnitude": round(float(centers[i][0] * std[0] + mean[0]), 1),
            "center_depth_km": round(float(centers[i][1] * std[1] + mean[1]), 1),
            "compactness": round(intra_dist, 3),
            "separation": round(separation, 3),
            "novelty_score": round(novelty, 3),
        })

    patterns.sort(key=lambda p: p["novelty_score"], reverse=True)
    anomalous = [p for p in patterns if p["novelty_score"] > 2.0]

    return {
        "n_patterns": len(patterns),
        "n_anomalous": len(anomalous),
        "patterns": patterns,
        "interpretation": f"{len(anomalous)}個の異常パターンを検出" if anomalous else "特異なパターンなし",
    }
