"""Unit tests for predict agent logic."""
from app.usecases.predict import _estimate_intensity, _estimate_aftershock_prob, _check_tsunami_risk
from app.domain.models import compute_severity


def test_estimate_intensity_typical():
    result = _estimate_intensity(6.0, 10.0, 100.0)
    assert 4.0 <= result <= 6.5


def test_estimate_intensity_clamp():
    assert _estimate_intensity(9.0, 5.0) <= 7.0
    assert _estimate_intensity(1.0, 500.0) >= 0.0


def test_aftershock_prob_range():
    assert 0.0 <= _estimate_aftershock_prob(5.5) <= 1.0


def test_aftershock_prob_larger_quake_higher():
    assert _estimate_aftershock_prob(7.0) > _estimate_aftershock_prob(4.0)


def test_tsunami_risk_yes():
    assert _check_tsunami_risk(7.0, 30.0) is True


def test_tsunami_risk_no_small():
    assert _check_tsunami_risk(5.0, 30.0) is False


def test_tsunami_risk_no_deep():
    assert _check_tsunami_risk(7.0, 100.0) is False


def test_severity_critical_tsunami():
    assert compute_severity(4.0, 0.1, True) == "CRITICAL"


def test_severity_critical_intensity():
    assert compute_severity(6.5, 0.1, False) == "CRITICAL"


def test_severity_high():
    assert compute_severity(5.5, 0.1, False) == "HIGH"


def test_severity_medium():
    assert compute_severity(4.5, 0.35, False) == "MEDIUM"


def test_severity_low():
    assert compute_severity(2.0, 0.1, False) == "LOW"
