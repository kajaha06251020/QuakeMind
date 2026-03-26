"""連合学習フレームワーク。データを共有せずにモデルを共同学習。"""
import logging
import numpy as np
logger = logging.getLogger(__name__)

class FederatedAggregator:
    def __init__(self):
        self.model_updates: list[dict] = []

    def receive_update(self, institution: str, weights: list[float], n_samples: int) -> None:
        self.model_updates.append({"institution": institution, "weights": np.array(weights), "n_samples": n_samples})

    def aggregate(self) -> dict:
        if not self.model_updates: return {"error": "更新データなし"}
        total_samples = sum(u["n_samples"] for u in self.model_updates)
        aggregated = np.zeros_like(self.model_updates[0]["weights"])
        for u in self.model_updates:
            w = u["n_samples"] / total_samples
            aggregated += u["weights"] * w
        return {"aggregated_weights": aggregated.tolist(), "n_institutions": len(self.model_updates), "total_samples": total_samples}

    def clear(self): self.model_updates = []

_aggregator = FederatedAggregator()

def submit_update(institution: str, weights: list[float], n_samples: int) -> dict:
    _aggregator.receive_update(institution, weights, n_samples)
    return {"status": "accepted", "institution": institution, "pending_updates": len(_aggregator.model_updates)}

def get_aggregated_model() -> dict:
    return _aggregator.aggregate()
