from app.usecases.fault_healing import estimate_healing_rate

def test_all_faults():
    result = estimate_healing_rate()
    assert result["n_analyzed"] > 0
    for f in result["faults"]:
        assert f["healing_rate_per_year"] > 0
        assert f["cycle_completeness"] >= 0

def test_specific_fault():
    result = estimate_healing_rate("南海")
    assert result["n_analyzed"] >= 1
    assert result["faults"][0]["fault"] == "南海トラフ"
