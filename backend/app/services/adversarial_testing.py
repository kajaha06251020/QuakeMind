"""敵対的テスト。予測の頑健性をストレステストする。"""
import logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
from app.usecases.ml_predictor import predict_large_earthquake

logger = logging.getLogger(__name__)


def adversarial_test(events: list[EarthquakeRecord], n_perturbations: int = 20) -> dict:
    if len(events) < 10:
        return {"error": "イベント数不足"}

    base = predict_large_earthquake(events)
    base_prob = base.get("probability", 0)

    rng = np.random.default_rng(42)
    perturbation_results = []

    # マグニチュード摂動
    for _ in range(n_perturbations // 2):
        perturbed = []
        for e in events:
            new_mag = e.magnitude + rng.normal(0, 0.3)
            new_mag = max(1.0, min(9.0, new_mag))
            perturbed.append(EarthquakeRecord(
                event_id=e.event_id, magnitude=round(new_mag, 1),
                latitude=e.latitude, longitude=e.longitude,
                depth_km=e.depth_km, timestamp=e.timestamp,
            ))
        p = predict_large_earthquake(perturbed)
        perturbation_results.append({"type": "magnitude_noise", "probability": p.get("probability", 0)})

    # イベント削除
    for _ in range(n_perturbations // 2):
        n_remove = max(1, len(events) // 5)
        indices = rng.choice(len(events), size=len(events) - n_remove, replace=False)
        subset = [events[i] for i in sorted(indices)]
        p = predict_large_earthquake(subset)
        perturbation_results.append({"type": "event_removal", "probability": p.get("probability", 0)})

    probs = [r["probability"] for r in perturbation_results]
    std = float(np.std(probs))
    max_change = max(abs(p - base_prob) for p in probs)

    robustness = max(0, 1 - std * 5)

    return {
        "base_probability": round(base_prob, 4),
        "perturbation_mean": round(float(np.mean(probs)), 4),
        "perturbation_std": round(std, 4),
        "max_change": round(max_change, 4),
        "robustness_score": round(robustness, 4),
        "vulnerability": "robust" if robustness > 0.7 else "moderate" if robustness > 0.4 else "fragile",
        "n_perturbations": len(perturbation_results),
    }
