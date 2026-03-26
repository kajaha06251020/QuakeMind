from app.usecases.rupture_propagation import simulate_rupture

def test_rupture_basic():
    result = simulate_rupture("nankai_west", 8.0, n_simulations=100)
    assert "rupture_length" in result
    assert result["rupture_length"]["mean_km"] >= 200
    assert result["segment_rupture_probabilities"]["nankai_west"]["probability"] == 1.0

def test_rupture_small_mag():
    result = simulate_rupture("tokai", 6.0, n_simulations=100)
    assert result["rupture_length"]["mean_km"] < 500

def test_rupture_invalid():
    result = simulate_rupture("nonexistent", 7.0)
    assert "error" in result
