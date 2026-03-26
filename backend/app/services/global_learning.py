"""グローバル地震学習DB。世界の大地震パターンとの類似度検索。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)

# 過去の大地震シーケンスのパターンDB（特徴量: [前30日のb値, 発生率変化, クラスタ数, 最大M])
_GLOBAL_PATTERNS = [
    {"name": "2011 東北M9.0", "year": 2011, "features": [0.75, 2.5, 4, 7.3], "outcome": "M9.0 巨大地震"},
    {"name": "2010 チリM8.8", "year": 2010, "features": [0.80, 1.8, 3, 6.5], "outcome": "M8.8 メガスラスト"},
    {"name": "2016 熊本M7.3", "year": 2016, "features": [0.90, 3.2, 5, 6.5], "outcome": "M7.3 内陸直下（前震-本震型）"},
    {"name": "2004 スマトラM9.1", "year": 2004, "features": [0.70, 1.5, 2, 7.0], "outcome": "M9.1 巨大津波"},
    {"name": "1995 阪神M7.3", "year": 1995, "features": [0.95, 1.0, 1, 5.0], "outcome": "M7.3 都市直下（前兆少）"},
    {"name": "2023 トルコM7.8", "year": 2023, "features": [0.85, 2.0, 3, 6.0], "outcome": "M7.8 横ずれ断層"},
    {"name": "2015 ネパールM7.8", "year": 2015, "features": [0.82, 1.3, 2, 5.5], "outcome": "M7.8 逆断層"},
    {"name": "正常活動パターン", "year": 0, "features": [1.00, 1.0, 0, 4.0], "outcome": "背景活動、大地震なし"},
]


def search_global_patterns(current_features: dict) -> dict:
    """現在の状況と類似する過去の世界の事例を検索する。"""
    query = [
        current_features.get("b_value", 1.0),
        current_features.get("rate_change_ratio", 1.0),
        current_features.get("n_clusters", 0),
        current_features.get("max_magnitude", 4.0),
    ]
    q = np.array(query, dtype=float)

    results = []
    for pattern in _GLOBAL_PATTERNS:
        p = np.array(pattern["features"], dtype=float)
        # コサイン類似度
        dot = np.dot(q, p)
        nq, np_ = np.linalg.norm(q), np.linalg.norm(p)
        sim = float(dot / (nq * np_)) if nq > 0 and np_ > 0 else 0

        results.append({
            "name": pattern["name"],
            "year": pattern["year"],
            "similarity": round(sim, 4),
            "outcome": pattern["outcome"],
            "features": pattern["features"],
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)

    top = results[0]
    return {
        "most_similar": top,
        "all_matches": results[:5],
        "query_features": query,
        "warning": f"現在の状況は「{top['name']}」と類似度{top['similarity']:.0%}。結果: {top['outcome']}" if top["similarity"] > 0.9 else None,
    }
