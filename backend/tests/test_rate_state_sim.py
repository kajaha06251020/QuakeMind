from app.usecases.rate_state_sim import simulate_rate_state


def test_unstable_regime():
    result = simulate_rate_state(a=0.01, b=0.015, duration_years=10, dt_years=0.1)
    assert result["a_minus_b"] < 0
    assert result["stability"] == "unstable (seismogenic)"


def test_stable_regime():
    result = simulate_rate_state(a=0.015, b=0.01, duration_years=10, dt_years=0.1)
    assert result["a_minus_b"] > 0
    assert result["stability"] == "stable (aseismic)"


def test_has_timeseries():
    result = simulate_rate_state(duration_years=5, dt_years=0.1)
    assert len(result["timeseries_sample"]) > 0
    assert "velocity_m_s" in result["timeseries_sample"][0]
