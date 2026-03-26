from app.usecases.focal_mechanism import classify_fault_type, estimate_rupture_area, parse_moment_tensor

def test_classify_strike_slip():
    assert classify_fault_type(0) == "strike_slip"
    assert classify_fault_type(180) == "strike_slip"

def test_classify_reverse():
    assert classify_fault_type(90) == "reverse"

def test_classify_normal():
    assert classify_fault_type(-90) == "normal"
    assert classify_fault_type(270) == "normal"

def test_rupture_area():
    result = estimate_rupture_area(7.0)
    assert result["rupture_area_km2"] > 100
    assert result["rupture_length_km"] > 10

def test_parse_moment_tensor_empty():
    assert parse_moment_tensor({}) is None
