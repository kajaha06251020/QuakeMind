from app.usecases.cascade import compute_cascade_probability


def test_cascade_basic():
    result = compute_cascade_probability(34.0, 137.0, 7.5)
    assert len(result["fault_cascade"]) > 0
    assert result["highest_risk_fault"] is not None
    for f in result["fault_cascade"]:
        assert 0 <= f["cascade_probability_7day"] <= 1


def test_cascade_small_eq():
    result = compute_cascade_probability(35.0, 139.0, 4.0)
    # 小さい地震はカスケード確率が低い
    for f in result["fault_cascade"]:
        assert f["cascade_probability_7day"] < 0.1


def test_cascade_near_nankai():
    result = compute_cascade_probability(33.0, 135.0, 8.0)
    nankai = next(f for f in result["fault_cascade"] if f["fault_id"] == "nankai")
    assert nankai["distance_km"] < 50
