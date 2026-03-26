"""転移学習フレームワーク。グローバルデータの特徴を日本データに適用する。"""
import logging
import math
import numpy as np

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


class FeatureStandardizer:
    """特徴量の標準化。グローバルデータで学習した統計量で日本データを変換する。"""

    def __init__(self):
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None
        self.n_features: int = 0

    def fit(self, features: np.ndarray) -> None:
        self.mean = np.mean(features, axis=0)
        self.std = np.std(features, axis=0)
        self.std[self.std == 0] = 1
        self.n_features = features.shape[1]

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self.mean is None:
            raise ValueError("fit() を先に実行してください")
        return (features - self.mean) / self.std

    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        self.fit(features)
        return self.transform(features)

    def to_dict(self) -> dict:
        return {
            "mean": self.mean.tolist() if self.mean is not None else None,
            "std": self.std.tolist() if self.std is not None else None,
            "n_features": self.n_features,
        }


def extract_transfer_features(events: list[EarthquakeRecord]) -> np.ndarray:
    """転移学習用の特徴量を抽出する。"""
    if not events:
        return np.array([]).reshape(0, 6)

    features = []
    for e in events:
        features.append([
            e.magnitude,
            e.depth_km,
            e.latitude,
            e.longitude,
            math.log10(max(e.depth_km, 0.1)),  # log depth
            e.magnitude ** 2,  # M^2 (エネルギー近似)
        ])
    return np.array(features)


def compute_domain_similarity(
    source_features: np.ndarray,
    target_features: np.ndarray,
) -> dict:
    """ソースドメイン（グローバル）とターゲットドメイン（日本）の類似度を計算する。"""
    if len(source_features) == 0 or len(target_features) == 0:
        return {"similarity": 0.0, "transferable": False}

    source_mean = np.mean(source_features, axis=0)
    target_mean = np.mean(target_features, axis=0)

    # コサイン類似度
    dot = np.dot(source_mean, target_mean)
    norm_s = np.linalg.norm(source_mean)
    norm_t = np.linalg.norm(target_mean)

    if norm_s == 0 or norm_t == 0:
        similarity = 0.0
    else:
        similarity = float(dot / (norm_s * norm_t))

    return {
        "similarity": round(similarity, 4),
        "transferable": similarity > 0.7,
        "source_n": len(source_features),
        "target_n": len(target_features),
    }
