import pytest
from app.usecases.coulomb_rate_state import coulomb_to_rate_change, rate_state_forecast

def test_positive_stress_increases_rate():
    factor = coulomb_to_rate_change(0.01)  # 0.01 MPa
    assert factor > 1.0

def test_negative_stress_decreases_rate():
    factor = coulomb_to_rate_change(-0.01)
    assert factor < 1.0

def test_zero_stress_no_change():
    factor = coulomb_to_rate_change(0.0)
    assert abs(factor - 1.0) < 0.01

def test_rate_state_forecast_basic():
    result = rate_state_forecast(background_rate=0.5, delta_cfs_mpa=0.01)
    assert result["rate_change_factor"] > 1.0
    assert result["cumulative_expected_events"] > 0
    assert len(result["timeseries"]) > 0

def test_rate_state_negative_stress():
    result = rate_state_forecast(background_rate=0.5, delta_cfs_mpa=-0.01)
    assert result["rate_change_factor"] < 1.0
