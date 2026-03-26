from app.usecases.multi_hazard_cascade import simulate_cascade

def test_m9_cascade():
    result = simulate_cascade(9.0, 15.0, 33.0, 135.0)
    assert result["n_phases"] >= 3  # shaking + tsunami + fire
    assert result["cascade_severity"] in ("catastrophic", "severe")

def test_m5_cascade():
    result = simulate_cascade(5.0, 20.0, 35.0, 139.0)
    assert result["n_phases"] >= 1

def test_small_no_cascade():
    result = simulate_cascade(3.0, 50.0, 35.0, 139.0)
    assert result["n_phases"] >= 1
    assert result["cascade_severity"] == "minor"
