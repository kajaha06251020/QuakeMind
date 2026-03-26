"""DBSCAN 時空間クラスタリング（群発地震検知）。"""
import logging
import math
from datetime import datetime, timezone

import numpy as np
from sklearn.cluster import DBSCAN

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0  # 緯度1度 ≈ 111km


def _parse_ts(e: EarthquakeRecord) -> float:
    try:
        dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def detect_clusters(
    events: list[EarthquakeRecord],
    spatial_km: float = 50.0,
    temporal_days: float = 7.0,
    min_samples: int = 3,
) -> dict:
    """
    DBSCAN で時空間クラスタリングを実行する。

    Args:
        events: 地震イベントリスト
        spatial_km: 空間的な近傍半径 (km)
        temporal_days: 時間的な近傍半径 (日)
        min_samples: クラスタの最小イベント数

    Returns:
        {"n_clusters": int, "noise_events": int, "clusters": [...]}
    """
    if len(events) < min_samples:
        return {"n_clusters": 0, "noise_events": len(events), "clusters": []}

    # 特徴行列: [lat_km, lon_km, time_days]
    lats = np.array([e.latitude for e in events])
    lons = np.array([e.longitude for e in events])
    times = np.array([_parse_ts(e) for e in events])

    lat_km = lats * _KM_PER_DEG
    lon_km = lons * _KM_PER_DEG * np.cos(np.radians(np.mean(lats)))
    time_days = (times - times.min()) / 86400.0

    # 正規化: spatial_km と temporal_days を同じスケールに
    X = np.column_stack([
        lat_km / spatial_km,
        lon_km / spatial_km,
        time_days / temporal_days,
    ])

    db = DBSCAN(eps=1.0, min_samples=min_samples, metric="euclidean")
    labels = db.fit_predict(X)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = int(np.sum(labels == -1))

    clusters = []
    for cid in range(n_clusters):
        mask = labels == cid
        cluster_events = [e for e, m in zip(events, mask) if m]
        cluster_lats = lats[mask]
        cluster_lons = lons[mask]
        cluster_times = times[mask]
        cluster_mags = np.array([e.magnitude for e in cluster_events])

        clusters.append({
            "cluster_id": cid,
            "n_events": len(cluster_events),
            "center_lat": round(float(cluster_lats.mean()), 4),
            "center_lon": round(float(cluster_lons.mean()), 4),
            "start": datetime.fromtimestamp(float(cluster_times.min()), tz=timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(float(cluster_times.max()), tz=timezone.utc).isoformat(),
            "max_magnitude": round(float(cluster_mags.max()), 1),
            "event_ids": [e.event_id for e in cluster_events],
        })

    # クラスタサイズ降順でソート
    clusters.sort(key=lambda c: c["n_events"], reverse=True)

    return {"n_clusters": n_clusters, "noise_events": noise_count, "clusters": clusters}
