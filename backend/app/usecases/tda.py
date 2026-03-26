"""トポロジカルデータ分析（TDA）。永続ホモロジーの簡易実装。"""
import math
import logging

import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0


def _distance_matrix(events: list[EarthquakeRecord]) -> np.ndarray:
    n = len(events)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dlat = (events[i].latitude - events[j].latitude) * _KM_PER_DEG
            dlon = (events[i].longitude - events[j].longitude) * _KM_PER_DEG * math.cos(math.radians(events[i].latitude))
            D[i, j] = D[j, i] = math.sqrt(dlat ** 2 + dlon ** 2)
    return D


def compute_persistence(events: list[EarthquakeRecord], max_radius_km: float = 200.0) -> dict:
    """VietorisRips フィルトレーションの簡易永続ホモロジー。

    H0（連結成分）の永続性を計算する。
    """
    n = len(events)
    if n < 5:
        return {"error": "最低5イベント必要", "betti_numbers": {}}

    D = _distance_matrix(events)

    # Union-Find for H0
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
            return True
        return False

    # エッジを距離でソート
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if D[i, j] <= max_radius_km:
                edges.append((D[i, j], i, j))
    edges.sort()

    # フィルトレーション
    birth_death_pairs = []  # (birth, death) for H0
    n_components = n

    for dist, i, j in edges:
        if union(i, j):
            # 成分がマージ: 1つが「死ぬ」
            birth_death_pairs.append((0.0, dist))
            n_components -= 1

    # 最後に残った成分は「永遠に生きる」
    for _ in range(n_components):
        birth_death_pairs.append((0.0, max_radius_km))

    # 永続性 = death - birth
    persistences = [d - b for b, d in birth_death_pairs if d < max_radius_km]

    # Betti numbers at different radii
    radii = np.linspace(0, max_radius_km, 20)
    betti_0 = []
    for r in radii:
        # r以下のエッジで連結成分数を計算
        p = list(range(n))

        def f(x, _p=p):
            while _p[x] != x:
                _p[x] = _p[_p[x]]
                x = _p[x]
            return x

        comps = n
        for dist, i, j in edges:
            if dist <= r and f(i) != f(j):
                p[f(i)] = f(j)
                comps -= 1
        betti_0.append(comps)

    return {
        "n_events": n,
        "persistence_pairs_h0": len(birth_death_pairs),
        "mean_persistence_km": round(float(np.mean(persistences)), 2) if persistences else 0,
        "max_persistence_km": round(float(max(persistences)), 2) if persistences else 0,
        "betti_curve": [{"radius_km": round(float(r), 1), "betti_0": int(b)} for r, b in zip(radii, betti_0)],
        "topological_complexity": round(float(np.std(persistences)), 3) if len(persistences) > 1 else 0,
    }
