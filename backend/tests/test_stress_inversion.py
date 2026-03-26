from app.usecases.stress_inversion import invert_stress_field


def test_inversion_basic():
    fms = [
        {"strike": 45, "dip": 60, "rake": 90},
        {"strike": 50, "dip": 55, "rake": 85},
        {"strike": 40, "dip": 65, "rake": 95},
    ]
    result = invert_stress_field(fms)
    assert "sigma1_azimuth" in result
    assert "tectonic_regime" in result
    assert result["tectonic_regime"] == "reverse"


def test_inversion_strike_slip():
    fms = [{"strike": 0, "dip": 90, "rake": 0} for _ in range(5)]
    result = invert_stress_field(fms)
    assert result["tectonic_regime"] == "strike_slip"


def test_inversion_insufficient():
    result = invert_stress_field([{"strike": 0, "dip": 45, "rake": 90}])
    assert "error" in result
