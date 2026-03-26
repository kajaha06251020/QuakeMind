from app.usecases.finite_fault import estimate_fault_geometry, generate_slip_distribution


def test_geometry_m7():
    result = estimate_fault_geometry(7.0, 15.0)
    assert result["rupture_length_km"] > 20
    assert result["rupture_area_km2"] > 100
    assert result["average_slip_m"] > 0.5


def test_geometry_m5():
    result = estimate_fault_geometry(5.0, 10.0)
    assert result["rupture_length_km"] < result["rupture_area_km2"]


def test_slip_distribution():
    result = generate_slip_distribution(50.0, 20.0, 2.0)
    assert result["max_slip_m"] > result["avg_slip_m"]
    assert len(result["slip_grid"]) == 10
    assert len(result["slip_grid"][0]) == 20
