import pytest
from app.usecases.bayesian_network import BayesianEarthquakeNetwork, unified_probability


def test_network_basic():
    net = BayesianEarthquakeNetwork()
    net.set_evidence(b_value_anomaly=0.8, rate_anomaly=0.6, stress_loading=0.5)
    result = net.infer()
    assert 0 < result["large_earthquake_probability"] < 1
    assert result["active_signals"] >= 2


def test_network_low_risk():
    net = BayesianEarthquakeNetwork()
    net.set_evidence(b_value_anomaly=0.0, rate_anomaly=0.0)
    result = net.infer()
    assert result["large_earthquake_probability"] < 0.3


def test_unified_probability():
    results = {"b_value_change": -0.3, "anomaly_detected": True, "p_value": 0.001, "n_clusters": 3}
    output = unified_probability(results)
    assert "unified_probability" in output
    assert "causal_explanation" in output
    assert output["risk_level"] in ("normal", "elevated", "high", "critical")


def test_explain():
    net = BayesianEarthquakeNetwork()
    net.set_evidence(b_value_anomaly=0.9, stress_loading=0.7)
    net.infer()
    expl = net.explain()
    assert len(expl) >= 1
