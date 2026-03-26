from app.services.decision_support import generate_recommendations


def test_critical():
    result = generate_recommendations("critical", 0.85)
    assert result["total_actions"] > 0
    assert len(result["actions"]["immediate"]) > 0


def test_normal():
    result = generate_recommendations("normal", 0.05)
    assert result["total_actions"] >= 1
    assert len(result["actions"]["immediate"]) == 0


def test_with_scenario():
    scenario = {"tsunami": {"risk": True, "earliest_arrival_min": 15}, "damage": {"affected_population": 500000}}
    result = generate_recommendations("critical", 0.9, scenario=scenario)
    immediate = [a["action"] for a in result["actions"]["immediate"]]
    assert any("避難" in a for a in immediate)
