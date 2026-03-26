from app.usecases.deep_earthquake import classify_deep_mechanism

def test_shallow():
    result = classify_deep_mechanism(20, 5.0)
    assert result["most_likely_mechanism"] == "brittle_fracture"

def test_intermediate():
    result = classify_deep_mechanism(150, 6.0)
    assert "dehydration" in result["most_likely_mechanism"] or "thermal" in result["most_likely_mechanism"]

def test_deep():
    result = classify_deep_mechanism(550, 7.0)
    assert "phase" in result["most_likely_mechanism"] or "transform" in result["most_likely_mechanism"]
    assert result["is_anomalous"] is True
    assert len(result["research_significance"]) > 0

def test_temperature():
    result = classify_deep_mechanism(400, 5.0)
    assert result["estimated_temperature_c"] > 1000
    assert result["estimated_pressure_gpa"] > 10
