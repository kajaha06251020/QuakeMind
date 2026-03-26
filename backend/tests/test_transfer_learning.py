import pytest
import numpy as np
from app.usecases.transfer_learning import FeatureStandardizer, extract_transfer_features, compute_domain_similarity
from app.domain.seismology import EarthquakeRecord


def test_standardizer():
    fs = FeatureStandardizer()
    X = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
    transformed = fs.fit_transform(X)
    assert abs(np.mean(transformed, axis=0)[0]) < 0.01
    assert abs(np.std(transformed, axis=0)[0] - 1.0) < 0.01


def test_extract_features():
    events = [
        EarthquakeRecord(
            event_id="t1",
            magnitude=5.0,
            latitude=35.0,
            longitude=139.0,
            depth_km=10.0,
            timestamp="2026-01-01T00:00:00Z",
        )
    ]
    features = extract_transfer_features(events)
    assert features.shape == (1, 6)


def test_domain_similarity():
    source = np.array([
        [5.0, 10.0, 35.0, 139.0, 1.0, 25.0],
        [4.0, 20.0, 34.0, 138.0, 1.3, 16.0],
    ])
    target = np.array([[5.1, 12.0, 35.1, 139.1, 1.08, 26.0]])
    result = compute_domain_similarity(source, target)
    assert result["similarity"] > 0.5
    assert result["source_n"] == 2
