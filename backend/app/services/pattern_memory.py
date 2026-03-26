"""パターンメモリ。過去の検出パターンを記憶し新データと比較する。"""
import logging
import numpy as np

from app.services.research_journal import add_entry

logger = logging.getLogger(__name__)

# メモリ内パターンストア（永続化は research_journal 経由）
_patterns: list[dict] = []


def store_pattern(name: str, feature_vector: list[float], metadata: dict | None = None) -> int:
    """パターンを記憶する。インデックスを返す。"""
    _patterns.append({
        "name": name,
        "vector": feature_vector,
        "metadata": metadata or {},
    })
    return len(_patterns) - 1


def find_similar_patterns(query_vector: list[float], top_k: int = 5, threshold: float = 0.5) -> list[dict]:
    """記憶されたパターンから類似のものを検索する。"""
    if not _patterns or not query_vector:
        return []

    q = np.array(query_vector)
    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return []

    results = []
    for i, p in enumerate(_patterns):
        v = np.array(p["vector"])
        v_norm = np.linalg.norm(v)
        if v_norm == 0:
            continue
        similarity = float(np.dot(q, v) / (q_norm * v_norm))
        if similarity >= threshold:
            results.append({
                "index": i,
                "name": p["name"],
                "similarity": round(similarity, 4),
                "metadata": p["metadata"],
            })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def get_all_patterns() -> list[dict]:
    """全パターンを返す。"""
    return [{"index": i, "name": p["name"], "metadata": p["metadata"], "vector_dim": len(p["vector"])} for i, p in enumerate(_patterns)]


def clear_patterns() -> None:
    """パターンをクリアする（テスト用）。"""
    _patterns.clear()
