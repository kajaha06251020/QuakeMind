from app.usecases.precursor_fusion import compute_precursor_score


def test_high_risk():
    result = compute_precursor_score({"b_value_drop": 0.4, "anomaly_p_value": 0.001, "coulomb_stress": 0.05})
    assert result["integrated_score"] > 0.3
    assert result["active_signals"] >= 2


def test_normal():
    result = compute_precursor_score({})
    assert result["integrated_score"] == 0
    assert result["risk_level"] == "normal"


def test_synergy_bonus():
    result = compute_precursor_score({"b_value_drop": 0.3, "anomaly_p_value": 0.01, "quiescence_ratio": 0.2, "coulomb_stress": 0.05})
    assert result["active_signals"] >= 3
